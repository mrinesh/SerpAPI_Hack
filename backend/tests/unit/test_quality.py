"""Price flags against a locality benchmark, and missing-data flags (F-12, ADR 0014)."""

import pytest

from app.pipeline.quality import flag_listing
from app.schemas.common import Level
from app.schemas.listing import QualityFlagKind
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef
from tests.unit.test_verification import candidate

BENCHMARK = Sourced(
    value=10_000.0,
    confidence=0.7,
    method=ExtractionMethod.LLM,
    sources=[SourceRef(engine="google", url="https://example.com", title="Rates in Whitefield")],
)


def with_rate(rate):
    listing = candidate()
    listing.price_per_sqft = Sourced(value=rate, confidence=0.8, method=ExtractionMethod.REGEX)
    return listing


def kinds(flags):
    return [flag.kind for flag in flags]


@pytest.mark.parametrize(("rate", "flagged"), [(3_900, True), (4_100, False), (75, True)])
def test_rate_far_below_the_area_level_is_flagged(rate, flagged):
    flags = flag_listing(with_rate(rate), BENCHMARK)
    assert (QualityFlagKind.TOO_GOOD_TO_BE_TRUE in kinds(flags)) is flagged
    if flagged:
        flag = flags[0]
        assert flag.severity is Level.HIGH
        assert "Rates in Whitefield" in flag.reason and "₹10,000/sq ft" in flag.reason


def test_rate_is_computed_from_price_and_size_when_not_quoted():
    listing = candidate()
    listing.price_per_sqft = Sourced(method=ExtractionMethod.REGEX)
    listing.price_inr.value, listing.size_sqft.value = 360_000, 4_800
    assert flag_listing(listing, BENCHMARK)[0].reason.startswith("₹75/sq ft is 0.8% ")


def test_no_benchmark_means_no_price_flag():
    assert flag_listing(with_rate(75), None) == []


def test_missing_price_and_size_are_low_severity():
    listing = candidate()
    listing.price_inr.value = listing.size_sqft.value = listing.price_per_sqft.value = None
    flags = flag_listing(listing, BENCHMARK)
    assert kinds(flags) == [QualityFlagKind.MISSING_PRICE, QualityFlagKind.MISSING_SIZE]
    assert {flag.severity for flag in flags} == {Level.LOW}
