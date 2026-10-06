"""Investment metrics and the rent level (F-09, ADR 0010, ADR 0017). Pure functions."""

import pytest

from app.pipeline.enrichment.rent_level import (
    RentExtract,
    RentPair,
    median_rate,
    rupee_amounts,
    supported_rate,
)
from app.pipeline.metrics import compute_metrics, measure_value
from app.pipeline.ranking import roi_score
from app.schemas.common import Level
from app.schemas.listing import QualityFlag, QualityFlagKind, Verification
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef
from tests.unit.test_verification import candidate, context

PRICE_LEVEL = Sourced(value=10_000.0, confidence=0.7, method=ExtractionMethod.LLM)
RENT = Sourced(
    value=30.0,
    confidence=0.6,
    method=ExtractionMethod.LLM,
    sources=[SourceRef(engine="google", url="https://example.com/rent")],
)
GROWTH = Sourced(value=29.0, confidence=0.7, method=ExtractionMethod.LLM)


def check(flags=()):
    return Verification(
        listing_id="candidate-1",
        match_score=70,
        verdict="partial",
        confidence=0.6,
        model="fake",
        flags=list(flags),
    )


def metrics(listing=None, flags=(), rent=RENT, growth=GROWTH, **profile):
    return compute_metrics(
        listing or candidate(),
        check(flags),
        context(**profile).profile,
        price_level=PRICE_LEVEL,
        rent_level=rent,
        area_growth=growth,
    )


def test_formulas():
    # candidate(): ₹60 L, 1,000 sq ft -> ₹6,000/sq ft
    found = metrics()
    assert found.price_per_sqft.value == 6_000
    assert found.price_vs_area_pct.value == -40
    assert found.est_monthly_rent_inr.value == 30_000
    assert found.rental_yield_pct.value == 6  # 30 * 12 / 6,000 * 100
    assert found.price_growth_pct.value == 29
    assert found.total_return_pct.value == 35
    assert all(
        m.method is ExtractionMethod.COMPUTED
        for m in (found.rental_yield_pct, found.total_return_pct)
    )
    assert found.rental_yield_pct.sources[0].url == "https://example.com/rent"


def test_yield_needs_no_size_but_rent_in_rupees_does():
    listing = candidate()
    listing.size_sqft.value = None
    listing.price_per_sqft = Sourced(value=6_000, confidence=0.8, method=ExtractionMethod.REGEX)
    found = metrics(listing)
    assert found.rental_yield_pct.value == 6
    assert found.est_monthly_rent_inr.value is None


def test_missing_inputs_give_missing_metrics_not_zero():
    listing = candidate()
    listing.price_inr.value = None
    found = metrics(listing, rent=None, growth=None)
    for metric in (
        found.price_per_sqft,
        found.price_vs_area_pct,
        found.rental_yield_pct,
        found.price_growth_pct,
        found.total_return_pct,
    ):
        assert metric.value is None and metric.confidence == 0
    assert found.meets_target_roi is None


def test_a_price_flagged_as_implausible_gets_no_yield():
    flag = QualityFlag(kind=QualityFlagKind.TOO_GOOD_TO_BE_TRUE, severity=Level.HIGH, reason="x")
    listing = candidate()
    listing.price_inr.value, listing.size_sqft.value = 360_000, 4_800  # ₹75/sq ft
    found = metrics(listing, flags=[flag])
    assert found.rental_yield_pct.value is None
    assert "implausibly low" in found.rental_yield_pct.note
    assert found.assessment_note.startswith("No target check: the price looks implausibly low")


def test_the_investors_growth_beats_the_area_figure():
    found = metrics(expected_growth_pct=5)
    assert found.price_growth_pct.value == 5 and "investor" in found.price_growth_pct.note
    assert found.total_return_pct.value == 11


@pytest.mark.parametrize(
    ("goal", "target", "expected_measure", "meets"),
    [
        ("rental_income", 6, 6, True),  # boundary: equal meets
        ("rental_income", 6.1, 6, False),
        ("appreciation", 30, 29, False),
        ("balanced", 35, 35, True),
    ],
)
def test_target_uses_the_goals_measure(goal, target, expected_measure, meets):
    found = metrics(goal=goal, target_roi_pct=target)
    assert measure_value(found) == expected_measure
    assert found.meets_target_roi is meets


@pytest.mark.parametrize(
    ("yield_pct", "target", "expected"),
    [(0, 4, 0), (4, 4, 66.7), (6, 4, 100), (9, 4, 100), (-2, 4, 0), (2, 0, 100), (-1, 0, 0)],
)
def test_roi_score_is_proportional_with_full_marks_at_one_and_a_half_times(
    yield_pct, target, expected
):
    found = metrics(goal="rental_income")
    found.rental_yield_pct.value = yield_pct
    assert roi_score(found, target) == pytest.approx(expected, abs=0.1)


def test_roi_score_is_missing_without_the_measure():
    assert roi_score(metrics(rent=None), 4) is None
    assert roi_score(None, 4) is None


# --- rent level, against snippets recorded in F-09 -----------------------------------------

WHITEFIELD = (
    "Flats for Rent in whitefield, Bangalore Karnataka ・ ₹45,000 + 4,000 maintenance. "
    "Semi Furnished 1370 sqft Family. Semi Furnished 1245 sqft All."
)
WHITEFIELD_MONTH = (
    "Flat for rent in Whitefield, Bangalore ₹38,000 / month + Deposit 2 months rent 850 "
    "sqft(79 sqm) Rental is positioned from 38,000 per month"
)
KORAMANGALA = (
    "₹6,000 / month 10,000 sqft(929 sqm) Plot area ・ ₹1.35 Lac / month 1,600 sqft(149 sqm) "
    "Plot area ・ ₹2.1 Lac / month + Deposit 5 months rent 4,000 sqft(372 sqm"
)
KORAMANGALA_FURNISHED = (
    "Furnished Commercial office space for rent in Koramangala, Bangalore ₹1.7 Lac / month + "
    "Deposit 10 months rent 1,800 sqft(167 sqm) 1800 sq.Ft.,"
)


def pair(rent, size, evidence, index=0):
    return RentPair(result_index=index, monthly_rent=rent, size_sqft=size, evidence=evidence)


@pytest.mark.parametrize(
    ("found", "snippet", "expected"),
    [
        (
            pair(45_000, 1370, "₹45,000 + 4,000 maintenance. Semi Furnished 1370 sqft"),
            WHITEFIELD,
            45_000 / 1370,
        ),
        (
            pair(38_000, 850, "₹38,000 / month + Deposit 2 months rent 850 sqft"),
            WHITEFIELD_MONTH,
            38_000 / 850,
        ),  # a deposit mentioned in words
        (pair(38_000, 850, "₹38,000 / month"), WHITEFIELD_MONTH, None),  # no size in the span
        (
            pair(170_000, 1800, "₹1.7 Lac / month + Deposit 10 months rent 1,800 sqft"),
            KORAMANGALA_FURNISHED,
            170_000 / 1800,
        ),
        (
            pair(6_000, 10_000, "₹6,000 / month 10,000 sqft(929 sqm) Plot area"),
            KORAMANGALA,
            None,
        ),  # plot
        (
            pair(46_000, 1370, "₹45,000 + 4,000 maintenance. Semi Furnished 1370 sqft"),
            WHITEFIELD,
            None,
        ),
        (pair(45_000, 1370, "₹45,000 for 1370 sqft"), WHITEFIELD, None),  # span not in snippet
    ],
)
def test_rent_pairs_must_be_quoted_whole_unit_rents(found, snippet, expected):
    result = supported_rate(found, snippet, "Flats for Rent")
    assert result == (pytest.approx(expected) if expected else None)


def test_rupee_amounts_read_lakhs_and_thousands():
    assert {170_000, 135_000, 35_000, 45_000} <= rupee_amounts("₹1.7 Lac, 1.35 Lacs, 35k, ₹45,000")


def test_rent_level_is_the_median_of_at_least_three_checked_pairs():
    snippets = [
        "Flats for rent: ₹30,000 / month 1,000 sqft",
        "Flats for rent: ₹40,000 / month 1,000 sqft",
        "Flats for rent: ₹50,000 / month 1,000 sqft",
    ]
    results = [{"index": i, "title": "Rent", "snippet": s} for i, s in enumerate(snippets)]
    pairs = [
        pair(30_000, 1000, "₹30,000 / month 1,000 sqft", 0),
        pair(40_000, 1000, "₹40,000 / month 1,000 sqft", 1),
        pair(50_000, 1000, "₹50,000 / month 1,000 sqft", 2),
        pair(99_000, 1000, "₹99,000 / month 1,000 sqft", 2),  # not quoted: ignored
    ]
    rate, used, checked = median_rate(RentExtract(pairs=pairs, confidence=0.8), results)
    assert (rate, checked, len(used)) == (40.0, 3, 3)
    assert median_rate(RentExtract(pairs=pairs[:2], confidence=0.8), results) is None


@pytest.mark.parametrize("note", ["starting price", "price range; lower bound used"])
def test_a_starting_price_or_range_withholds_price_dependent_metrics(note):
    listing = candidate()
    listing.price_inr.note = note
    found = metrics(listing)
    assert found.price_vs_area_pct.value is None
    assert found.rental_yield_pct.value is None and found.total_return_pct.value is None
    assert "unconfirmed" in found.rental_yield_pct.note
    assert found.meets_target_roi is None
    assert found.assessment_note == (
        "No target check: the final unit price is unconfirmed (a range or starting price)."
    )
    assert found.price_growth_pct.value == 29  # growth does not depend on the price


def test_an_appreciation_verdict_does_not_depend_on_an_unconfirmed_price():
    listing = candidate()
    listing.price_inr.note = "starting price"
    found = metrics(listing, goal="appreciation", target_roi_pct=20)
    assert found.meets_target_roi is True and found.assessment_note is None


def test_the_target_is_frozen_into_the_metrics():
    assert metrics(target_roi_pct=3.5).target_roi_pct == 3.5


@pytest.mark.parametrize(
    ("kwargs", "note"),
    [
        ({"rent": None}, "No target check: missing an area rent level."),
        (
            {"rent": None, "growth": None, "goal": "balanced"},
            "No target check: missing an area rent level and a price growth figure for this "
            "locality.",
        ),
        (
            {"growth": None, "goal": "appreciation"},
            "No target check: missing a price growth figure for this locality.",
        ),
    ],
)
def test_missing_inputs_explain_the_missing_verdict(kwargs, note):
    found = metrics(**kwargs)
    assert found.meets_target_roi is None and found.assessment_note == note


def test_a_verdict_has_no_assessment_note():
    assert metrics().assessment_note is None
