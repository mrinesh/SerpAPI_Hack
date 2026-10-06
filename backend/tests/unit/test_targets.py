"""Suggested target ROI: multi-year growth, typical values, risk and rounding (ADR 0018)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import AreaIntelRow
from app.pipeline import targets
from app.pipeline.enrichment.area import (
    LongRunGrowthExtract,
    annualised,
    supported_long_run,
)
from app.pipeline.targets import area_yield, combine, round_target, typical_value
from app.reference import load_market
from app.schemas.area import AreaIntel
from app.schemas.profile import ROIMeasure
from app.schemas.provenance import ExtractionMethod, Sourced
from app.schemas.target import TargetSuggestionIn, TargetSuggestionPart

WHITEFIELD = (
    "Based on government registration data, flat prices appreciated by approximately 29% in "
    "the last one year, 96% over three years, and 145% over ..."
)
KORAMANGALA = "Koramangala property prices have changed +26.9% in 1 year & +92.2% in last 5 years."


def long_run(total, years, evidence, confidence=0.9):
    return LongRunGrowthExtract(
        result_index=0, total_pct=total, years=years, evidence=evidence, confidence=confidence
    )


def test_annualised_compounds():
    assert annualised(96, 3) == pytest.approx(25.15, abs=0.01)
    assert annualised(92.2, 5) == pytest.approx(13.96, abs=0.01)
    assert annualised(-20, 2) == pytest.approx(-10.56, abs=0.01)


@pytest.mark.parametrize(
    ("found", "snippet", "expected"),
    [
        (long_run(96, 3, "96% over three years"), WHITEFIELD, 25.15),
        (long_run(92.2, 5, "+92.2% in last 5 years"), KORAMANGALA, 13.96),
        (long_run(29, 1, "29% in the last one year"), WHITEFIELD, None),  # one year
        (long_run(96, 4, "96% over three years"), WHITEFIELD, None),  # wrong period
        (long_run(95, 3, "96% over three years"), WHITEFIELD, None),  # wrong number
        (long_run(-96, 3, "96% over three years"), WHITEFIELD, None),  # sign without a fall word
        (long_run(96, 3, "96% over 3 years"), WHITEFIELD, None),  # span not in the snippet
        (long_run(300, 12, "300% over 12 years"), "Prices rose 300% over 12 years.", None),
        (long_run(96, 3, "96% over three years", 0), WHITEFIELD, None),
    ],
)
def test_long_run_growth_must_be_a_quoted_multi_year_change(found, snippet, expected):
    result = supported_long_run(found, snippet)
    assert result == (pytest.approx(expected, abs=0.01) if expected is not None else None)


def sourced(value, confidence=0.7):
    return Sourced(value=value, confidence=confidence, method=ExtractionMethod.LLM)


def test_area_yield_and_typical_values():
    yield_ = area_yield(sourced(32.5), sourced(12_150))  # recorded Whitefield levels
    assert yield_.value == pytest.approx(3.21, abs=0.01)
    growth = sourced(25.15)
    assert typical_value(ROIMeasure.RENTAL_YIELD, yield_, growth) is yield_
    assert typical_value(ROIMeasure.PRICE_GROWTH, yield_, growth) is growth
    assert typical_value(ROIMeasure.TOTAL_RETURN, yield_, growth).value == pytest.approx(28.36)
    assert typical_value(ROIMeasure.TOTAL_RETURN, None, growth) is None
    assert area_yield(None, sourced(12_150)) is None


@pytest.mark.parametrize(
    ("value", "expected"), [(3.21, 3.0), (3.26, 3.5), (5.79, 6.0), (0.1, 0.5), (25.15, 25.0)]
)
def test_round_target_to_half_percent_with_a_floor(value, expected):
    assert round_target(value) == expected


def part(value, locality="Whitefield"):
    return TargetSuggestionPart(
        locality=locality, property_type="apartment", typical=sourced(value)
    )


@pytest.mark.parametrize(
    ("risk", "expected"), [("conservative", 3.0), ("balanced", 3.0), ("aggressive", 3.5)]
)
def test_risk_appetite_adjusts_the_typical_value(risk, expected):
    suggestion = combine(ROIMeasure.RENTAL_YIELD, [part(3.21)], risk)
    assert suggestion.target_roi_pct == expected and suggestion.typical_pct == 3.21
    assert "flat in Whitefield 3.2%" in suggestion.basis


def test_several_localities_use_the_median():
    parts = [part(3.0, "A"), part(4.0, "B"), part(9.0, "C")]
    assert combine(ROIMeasure.RENTAL_YIELD, parts, "balanced").typical_pct == 4.0


def test_no_data_means_no_suggestion():
    suggestion = combine(ROIMeasure.RENTAL_YIELD, [], "balanced")
    assert suggestion.target_roi_pct is None and "enter your own" in suggestion.basis


def test_cached_area_levels_are_used_before_any_lookup(db, monkeypatch):
    now = datetime.now(UTC)
    area = AreaIntel(
        locality_key="bengaluru/whitefield",
        locality="Whitefield",
        city="Bengaluru",
        price_levels={"apartment": sourced(12_000)},
        rent_levels={"apartment": sourced(30)},
        fetched_at=now,
        expires_at=now + timedelta(days=7),
    )
    db.add(AreaIntelRow(locality_key=area.locality_key, data=area.model_dump(mode="json"),
                        expires_at=area.expires_at))  # fmt: skip
    db.commit()

    def no_lookup(*_args, **_kwargs):
        raise AssertionError("cached values should be used")

    monkeypatch.setattr(targets, "searched_level", no_lookup)
    monkeypatch.setattr(targets, "rent_level", no_lookup)
    data = TargetSuggestionIn(
        segment="residential",
        property_types=["apartment"],
        localities=["whitefield"],
        goal="rental_income",
        risk_appetite="balanced",
    )
    suggestion = targets.suggest_target(db, targets.Settings(), load_market("Bengaluru"), data)
    assert suggestion.typical_pct == 3.0 and suggestion.target_roi_pct == 3.0
