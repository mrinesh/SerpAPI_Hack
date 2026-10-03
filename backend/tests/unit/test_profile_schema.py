import pytest
from pydantic import ValidationError

from app.schemas.profile import InvestorProfileIn


def _profile(**overrides):
    base = {
        "name": "Rental yield, East Bengaluru",
        "segment": "residential",
        "property_types": ["apartment"],
        "budget_max_inr": 8_000_000,
    }
    return InvestorProfileIn(**(base | overrides))


def test_minimal_profile_is_valid():
    assert _profile().city == "Bengaluru"


def test_budget_range_is_checked():
    with pytest.raises(ValidationError):
        _profile(budget_min_inr=9_000_000)
