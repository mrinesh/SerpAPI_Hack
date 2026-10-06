"""F-09: arithmetic, goal comparison, provenance and uncertain denominators."""

from types import SimpleNamespace

import pytest

from app.pipeline.metrics import compute_metrics
from app.schemas.provenance import Sourced, SourceRef
from tests.unit.test_verification import candidate, context


def fact(value, confidence=0.6, url="https://example.com/rent"):
    return Sourced(
        value=value,
        confidence=confidence,
        method="regex",
        sources=[SourceRef(engine="google", url=url)],
        note="quoted input",
    )


def metrics(**kwargs):
    return compute_metrics(
        candidate(),
        SimpleNamespace(price_levels={"apartment": fact(7500)}),
        context(**kwargs).profile,
        rent=fact(25000),
        growth=fact(8),
    )


def test_formula_and_sources_use_full_precision_and_weakest_confidence():
    result = metrics()
    assert result.price_per_sqft.value == 6000
    assert result.price_vs_area_pct.value == pytest.approx(-20)
    assert result.rental_yield_pct.value == 5
    assert result.price_growth_pct.value == 8
    assert result.total_return_pct.value == 13
    assert result.total_return_pct.method == "computed"
    assert result.total_return_pct.confidence == 0.6
    assert len(result.total_return_pct.sources) == 2  # duplicate rent/growth source removed
    assert "before costs" in result.rental_yield_pct.note


@pytest.mark.parametrize(
    "goal,target,expected",
    [
        ("rental_income", 5, True),
        ("rental_income", 5.000001, False),
        ("appreciation", 8, True),
        ("appreciation", 9, False),
        ("balanced", 13, True),
        ("balanced", 14, False),
    ],
)
def test_goal_specific_target_and_exact_boundary(goal, target, expected):
    assert metrics(goal=goal, target_roi_pct=target).meets_target_roi is expected


def test_override_zero_and_negative_are_assumptions_not_missing():
    assert metrics(expected_growth_pct=0).total_return_pct.value == 5
    result = metrics(expected_growth_pct=-10, goal="balanced", target_roi_pct=0)
    assert result.total_return_pct.value == -5
    assert result.meets_target_roi is False
    assert result.price_growth_pct.method == "query"
    assert result.price_growth_pct.sources == []
    assert "assumption" in result.price_growth_pct.note


@pytest.mark.parametrize(
    "field,value",
    [
        ("price_inr", None),
        ("price_inr", 0),
        ("price_inr", -1),
        ("size_sqft", None),
        ("size_sqft", 0),
    ],
)
def test_absent_or_invalid_inputs_do_not_divide_by_zero(field, value):
    result = compute_metrics(
        candidate(**{field: fact(value)}), None, context().profile, rent=fact(25000)
    )
    assert result.price_per_sqft.value is None
    assert result.price_vs_area_pct.value is None
    if field == "price_inr":
        assert result.rental_yield_pct.value is None
        assert result.meets_target_roi is None


def test_missing_growth_does_not_block_rental_goal_and_missing_rent_does_not_block_growth_goal():
    rental = compute_metrics(
        candidate(), None, context(goal="rental_income").profile, rent=fact(25000)
    )
    assert rental.meets_target_roi is not None and rental.total_return_pct.value is None
    growth = compute_metrics(
        candidate(), None, context(goal="appreciation").profile, growth=fact(-2)
    )
    assert growth.meets_target_roi is False and growth.rental_yield_pct.value is None
    balanced = compute_metrics(
        candidate(), None, context(goal="balanced").profile, rent=fact(25000)
    )
    assert balanced.meets_target_roi is None


@pytest.mark.parametrize("reason", ["Not checked", "Implausibly cheap quote", None])
def test_uncertain_price_never_passes_roi(reason):
    listing = candidate()
    if reason is None:
        listing.price_inr.note = "price range; lower bound used"
    result = compute_metrics(
        listing, None, context().profile, rent=fact(25000), blocked_reason=reason
    )
    assert result.meets_target_roi is None and result.rental_yield_pct.value is None
    assert result.assessment_note


def test_quoted_rate_without_size_and_wrong_type_benchmark():
    listing = candidate(size_sqft=fact(None), price_per_sqft=fact(6000))
    result = compute_metrics(
        listing, SimpleNamespace(price_levels={"office": fact(10000)}), context().profile
    )
    assert result.price_per_sqft.value == 6000
    assert result.area_avg_price_per_sqft.value is None


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_inputs_do_not_escape_to_json(value):
    result = compute_metrics(candidate(size_sqft=fact(value)), None, context().profile)
    assert result.price_per_sqft.value is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 200, -101])
def test_invalid_growth_cannot_pass_an_appreciation_target(value):
    result = compute_metrics(
        candidate(), None, context(goal="appreciation").profile, growth=fact(value)
    )
    assert result.price_growth_pct.value is None and result.meets_target_roi is None
