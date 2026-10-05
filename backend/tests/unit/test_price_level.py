"""Locality price levels: grounded search extraction and the run-median fallback (ADR 0014)."""

from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.core.errors import ReplayMiss
from app.pipeline.enrichment.price_level import (
    PriceLevelExtract,
    peer_median,
    price_levels,
    supported_rate,
)
from app.reference import load_market
from app.schemas.profile import PropertyType
from app.schemas.provenance import ExtractionMethod, Sourced
from tests.unit.test_verification import candidate, context

SNIPPET = "Average price of flats in Whitefield is ₹7,200 - ₹8,800 per sq ft as of 2026."


def extract(low, high=None, evidence="₹7,200 - ₹8,800 per sq ft", confidence=0.8):
    return PriceLevelExtract(
        result_index=0, low=low, high=high, evidence=evidence, confidence=confidence
    )


@pytest.mark.parametrize(
    ("found", "expected"),
    [
        (extract(7200, 8800), 8000),
        (extract(7200, evidence="₹7,200 - ₹8,800 per sq ft"), 7200),
        (extract(7300, 8800), None),  # number not in the span
        (extract(7200, 8800, evidence="₹7,200 - ₹9,000 per sq ft"), None),  # span not in snippet
        (extract(7200, 8800, evidence="₹7,200 - ₹8,800"), None),  # no per-sq-ft wording
        (extract(7200, 8800, confidence=0), None),
        (extract(None), None),
    ],
)
def test_rate_must_be_quoted_in_the_snippet(found, expected):
    assert supported_rate(found, SNIPPET) == expected


def test_portal_rate_page_wording_is_accepted():
    # Recorded 99acres-style snippet for Koramangala offices (fixtures/serpapi/google).
    snippet = (
        "Office Space (Average Price ₹/Sq-ft) ₹17501/Sq-ft. Lowest Locality Price ₹13094/sq-ft"
    )
    found = extract(17501, 17501, evidence="Office Space (Average Price ₹/Sq-ft) ₹17501/Sq-ft")
    assert supported_rate(found, snippet) == 17501


def test_rents_are_not_sale_rates():
    snippet = "Office rent in Koramangala is ₹75 per sq ft per month."
    assert supported_rate(extract(75, evidence="₹75 per sq ft per month"), snippet) is None


def rated(rate, method=ExtractionMethod.REGEX, **overrides):
    listing = candidate(**overrides)
    listing.price_per_sqft = Sourced(value=rate, confidence=0.8, method=method)
    return listing


def test_peer_median_needs_three_quoted_rates_of_the_same_kind():
    peers = [rated(5_000), rated(7_000), rated(9_000), rated(100, ExtractionMethod.COMPUTED)]
    median = peer_median(peers, "whitefield", PropertyType.APARTMENT)
    assert median.value == 7_000 and median.method is ExtractionMethod.COMPUTED
    assert peer_median(peers[:2], "whitefield", PropertyType.APARTMENT) is None
    assert peer_median(peers, "koramangala", PropertyType.APARTMENT) is None


class Serp:
    def __init__(self, error=None):
        self.error, self.queries = error, []

    def search(self, engine, params, run_id=None):
        self.queries.append(params["q"])
        if self.error:
            raise self.error
        results = [{"title": "Whitefield rates", "link": "https://example.com", "snippet": SNIPPET}]
        return SimpleNamespace(data={"organic_results": results}, search_id="s-1")


class LevelLLM:
    def __init__(self, found):
        self.found = found

    def generate_structured(self, **kwargs):
        assert kwargs["task"] == "extract_price_level"
        return self.found


def run_ctx(serp, llm):
    ctx = context()
    ctx.serp, ctx.llm, ctx.settings, ctx.run_id = serp, llm, get_settings(), "run-1"
    return ctx


def test_searched_level_is_sourced_and_one_search_per_locality_and_type():
    serp = Serp()
    listings = [rated(5_000), rated(6_000)]
    levels, notes = price_levels(
        run_ctx(serp, LevelLLM(extract(7200, 8800))), load_market("Bengaluru"), listings
    )
    level = levels[("whitefield", PropertyType.APARTMENT)]
    assert level.value == 8_000 and level.method is ExtractionMethod.LLM
    assert level.sources[0].url == "https://example.com" and level.sources[0].search_id == "s-1"
    assert serp.queries == ["flat price per sq ft in Whitefield Bangalore"]
    assert notes == ["flat in Whitefield: ₹8,000/sq ft (search)"]


def test_failed_search_falls_back_to_the_run_median():
    listings = [rated(5_000), rated(7_000), rated(9_000)]
    levels, _ = price_levels(
        run_ctx(Serp(ReplayMiss("no fixture")), None), load_market("Bengaluru"), listings
    )
    assert levels[("whitefield", PropertyType.APARTMENT)].value == 7_000
