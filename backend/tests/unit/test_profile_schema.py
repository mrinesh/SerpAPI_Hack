import pytest
from pydantic import ValidationError

from app.schemas.profile import GOAL_MEASURE, InvestmentGoal, InvestorProfileIn, ROIMeasure

RESIDENTIAL = {
    "name": "Rental income, East Bengaluru",
    "segment": "residential",
    "property_types": ["apartment"],
    "localities": ["whitefield"],
    "budget_max_inr": 8_000_000,
    "goal": "rental_income",
    "target_roi_pct": 4,
    "risk_appetite": "balanced",
}
COMMERCIAL = RESIDENTIAL | {
    "name": "Cafe space",
    "segment": "commercial",
    "property_types": ["shop_showroom"],
    "business_type": "Cafe",
}


def field_errors(data: dict) -> dict[str, str]:
    """Validate `data` and return {field: message} for every error."""
    with pytest.raises(ValidationError) as excinfo:
        InvestorProfileIn(**data)
    return {
        str(e["loc"][0]): e["msg"].removeprefix("Value error, ") for e in excinfo.value.errors()
    }


def test_valid_residential_and_commercial_profiles():
    residential = InvestorProfileIn(**RESIDENTIAL)
    assert residential.city == "Bengaluru"
    assert residential.business_type is None
    assert InvestorProfileIn(**COMMERCIAL).business_type == "Cafe"


def test_text_is_trimmed():
    profile = InvestorProfileIn(
        **RESIDENTIAL | {"name": "  Yield  ", "must_haves": [" near metro "]}
    )
    assert profile.name == "Yield"
    assert profile.must_haves == ["near metro"]


def test_property_types_must_belong_to_segment():
    errors = field_errors(RESIDENTIAL | {"property_types": ["apartment", "office"]})
    assert errors == {"property_types": "Office Space is not a residential property type"}


def test_property_types_must_not_repeat():
    assert "property_types" in field_errors(RESIDENTIAL | {"property_types": ["plot", "plot"]})


def test_commercial_requires_business_type():
    for missing in ({}, {"business_type": ""}, {"business_type": "   "}):
        data = {k: v for k, v in COMMERCIAL.items() if k != "business_type"} | missing
        assert field_errors(data) == {
            "business_type": "business type is required for commercial profiles"
        }


def test_residential_rejects_business_type():
    errors = field_errors(RESIDENTIAL | {"business_type": "Cafe"})
    assert errors == {"business_type": "business type applies only to commercial profiles"}


@pytest.mark.parametrize(
    "localities",
    [[], ["whitefield", "hebbal", "yelahanka", "jayanagar", "bellandur", "koramangala"]],
)
def test_one_to_five_localities(localities):
    assert "localities" in field_errors(RESIDENTIAL | {"localities": localities})


def test_localities_must_not_repeat():
    errors = field_errors(RESIDENTIAL | {"localities": ["hebbal", "hebbal"]})
    assert errors == {"localities": "localities must not repeat"}


def test_must_haves_must_not_be_blank():
    assert "must_haves" in field_errors(RESIDENTIAL | {"must_haves": ["near metro", "  "]})


def test_budget_and_size_ranges():
    errors = field_errors(RESIDENTIAL | {"budget_min_inr": 9_000_000})
    assert errors == {"budget_max_inr": "maximum budget must be at least the minimum budget"}
    errors = field_errors(RESIDENTIAL | {"size_min_sqft": 1500, "size_max_sqft": 1000})
    assert errors == {"size_max_sqft": "maximum size must be at least the minimum size"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_roi_pct", -1),
        ("target_roi_pct", 101),
        ("expected_growth_pct", -101),
        ("expected_growth_pct", 101),
    ],
)
def test_percentage_bounds(field, value):
    assert field in field_errors(RESIDENTIAL | {field: value})


def test_negative_expected_growth_is_allowed():
    assert InvestorProfileIn(**RESIDENTIAL | {"expected_growth_pct": -5}).expected_growth_pct == -5


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "segment",
        "property_types",
        "localities",
        "budget_max_inr",
        "goal",
        "target_roi_pct",
        "risk_appetite",
    ],
)
def test_required_fields(field):
    data = {k: v for k, v in RESIDENTIAL.items() if k != field}
    assert field in field_errors(data)


def test_each_goal_picks_its_roi_measure():
    assert GOAL_MEASURE == {
        InvestmentGoal.RENTAL_INCOME: ROIMeasure.RENTAL_YIELD,
        InvestmentGoal.APPRECIATION: ROIMeasure.PRICE_GROWTH,
        InvestmentGoal.BALANCED: ROIMeasure.TOTAL_RETURN,
    }
