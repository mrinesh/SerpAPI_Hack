"""Reject hallucinated amounts, mismatched comparables, deposits and non-annual trends."""

from types import SimpleNamespace

import pytest

from app.config import Settings
from app.core.errors import ReplayMiss
from app.pipeline.enrichment.investment import (
    InvestmentInputs,
    QuoteSelection,
    supported_growth,
    supported_rent,
)
from app.reference import load_market
from tests.unit.test_metrics import fact
from tests.unit.test_verification import candidate, context


@pytest.mark.parametrize(
    "quote,kind,bhk,expected",
    [
        ("2 BHK apartment in Whitefield Rs 25,000 per month", "apartment", 2, 25000),
        ("2 BHK flat in Whitefield INR 0.3 lakh monthly", "apartment", 2, 30000),
        ("Whitefield office space INR 75 per sqft per month", "office", None, 75),
        ("3 BHK flat Rs 25000 monthly", "apartment", 2, None),
        ("2 BHK flat Rs 25000 per day", "apartment", 2, None),
        ("2 BHK flat Rs 25000 - 35000 per month", "apartment", 2, None),
        ("2 BHK flat starting Rs 25000 monthly", "apartment", 2, None),
        ("2 BHK flat Rs 25000 rent and Rs 100000 deposit monthly", "apartment", 2, None),
        ("office INR 25000 monthly", "office", None, None),
        ("Office INR 9000 per month per person in 1000 sqft", "office", None, None),
        ("Koramangala office rent INR 170000 per month. 1800 sqft", "office", None, 170000 / 1800),
        (
            "Koramangala office rent INR 170000 per month. 1800 sqft and 2200 sqft",
            "office",
            None,
            None,
        ),
        ("2 BHK flat USD 25000 monthly", "apartment", 2, None),
    ],
)
def test_rent_units_and_comparability(quote, kind, bhk, expected):
    assert supported_rent(quote, kind, bhk) == expected


@pytest.mark.parametrize(
    "quote,expected",
    [
        ("Apartment prices grew 8% YoY", 8),
        ("Apartment prices fell 4% last year", -4),
        ("Apartment price growth 0% past 12 months", 0),
        ("Flat rates changed by 10.8% in the last 1 year", 10.8),
        ("Prices grew 8% over five years", None),
        ("Prices expected to grow 8% YoY", None),
        ("Rental yield grew 8% YoY", None),
        ("Prices grew 8% YoY and 2% quarterly", None),
    ],
)
def test_growth_is_reported_annual_change_only(quote, expected):
    assert supported_growth(quote) == expected


def fake_inputs(quote, evidence=None):
    calls = []
    serp = SimpleNamespace(
        search=lambda *a, **k: (
            calls.append(a)
            or SimpleNamespace(
                search_id="search-1",
                data={
                    "organic_results": [
                        {"title": "Rents", "link": "https://example.com", "snippet": quote}
                    ]
                },
            )
        )
    )
    llm = SimpleNamespace(
        generate_structured=lambda **_: QuoteSelection(
            result_index=0, evidence=evidence if evidence is not None else quote, confidence=0.9
        )
    )
    ctx = context(llm)
    ctx.serp, ctx.settings, ctx.run_id = serp, Settings(_env_file=None), "run-1"
    return InvestmentInputs(ctx, load_market("Bengaluru")), calls


def test_cohort_reuses_quote_and_propagates_original_search_source():
    inputs, calls = fake_inputs("2 BHK apartment in Whitefield Rs 25,000 per month")
    listing = candidate(bedrooms=fact(2))
    assert inputs.rent(listing).value == 25000
    assert inputs.rent(listing).sources[0].search_id == "search-1"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "quote,evidence",
    [
        (
            "2 BHK apartment in Whitefield Rs 25,000 per month",
            "2 BHK apartment in Whitefield Rs 50000 per month",
        ),
        ("2 BHK apartment in Koramangala Rs 25,000 per month", None),
        ("2 BHK apartment in Whitefield Extension Rs 25,000 per month", None),
    ],
)
def test_invented_quote_or_wrong_locality_is_unavailable(quote, evidence):
    inputs, _ = fake_inputs(quote, evidence)
    assert inputs.rent(candidate(bedrooms=fact(2))).value is None


def test_commercial_rate_scales_per_candidate_without_researching():
    inputs, calls = fake_inputs("Whitefield office space INR 75 per sqft per month")
    listing = candidate(property_type=fact("office"), size_sqft=fact(1000))
    assert inputs.rent(listing).value == 75000
    listing.size_sqft = fact(2000)
    assert inputs.rent(listing).value == 150000
    assert len(calls) == 1


def test_missing_recording_becomes_visible_missing_input_and_memoized_warning():
    inputs, _ = fake_inputs("irrelevant")

    def fail(*args, **kwargs):
        raise ReplayMiss("Record the rent search")

    inputs.ctx.serp.search = fail
    listing = candidate(bedrooms=fact(2))
    assert "replay_miss" in inputs.rent(listing).note
    assert inputs.rent(listing).value is None
    assert len(inputs.warnings) == 1


def test_unknown_bhk_and_override_avoid_unnecessary_searches():
    inputs, calls = fake_inputs("irrelevant")
    assert inputs.rent(candidate(size_sqft=fact(None))).value is None
    inputs.ctx.profile.expected_growth_pct = 0
    inputs.growth(candidate())
    assert calls == []


def test_unknown_housing_layout_needs_explicit_monthly_per_area_rate():
    inputs, _ = fake_inputs("Whitefield apartment rent Rs 30 per sqft per month")
    assert inputs.rent(candidate()).value == 30000
    wrong, _ = fake_inputs("Whitefield apartment rent Rs 30000 per month")
    assert wrong.rent(candidate()).value is None


def test_rent_quote_cannot_drop_units_or_qualifiers_from_a_valid_snippet():
    inputs, _ = fake_inputs(
        "2 BHK apartment in Whitefield Rs 25,000 per month", "Rs 25,000 per month"
    )
    assert "complete snippet" in inputs.rent(candidate(bedrooms=fact(2))).note
