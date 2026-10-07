"""Verification against a fake LLM: evidence grounding, hard constraints and uncertainty."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.integrations.llm.base import ModelTier
from app.pipeline.verification import (
    PROMPTS,
    ExtractedListing,
    VerificationAssessment,
    _supported_value,
    extract,
    listing_input,
    prompt_for,
    verify,
)
from app.schemas.common import SerpEngine
from app.schemas.listing import Listing, MatchVerdict, Portal, ResultKind
from app.schemas.profile import InvestorProfile, PropertyType
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef
from tests.unit.test_profile_schema import RESIDENTIAL


class FakeLLM:
    name = "fake"

    def __init__(self, extraction=None, assessment=None):
        self.calls = []
        self.extraction = extraction or ExtractedListing.model_validate(
            {
                field: {"value": None, "confidence": 0, "evidence": None}
                for field in ExtractedListing.model_fields
            }
        )
        self.assessment = assessment or VerificationAssessment(
            match_score=95, verdict="strong", matched_criteria=["Within budget"], confidence=0.95
        )

    def model_for(self, tier):
        return "fake-reasoning" if tier == ModelTier.REASONING else "fake-lite"

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["task"] == "classify_news":
            import json

            from app.pipeline.enrichment.area import ClassifiedNews

            inputs = json.loads(kwargs["prompt"].split("INPUT JSON:\n", 1)[1])["news_items"]
            return ClassifiedNews.model_validate(
                {
                    "items": [
                        {"index": n["index"], "topic": "other", "sentiment": "neutral"}
                        for n in inputs
                    ]
                }
            )
        if kwargs["task"] == "extract_rent":
            from app.pipeline.enrichment.rent_level import RentExtract

            return RentExtract(pairs=[], confidence=0)
        if kwargs["task"] == "extract_price_growth":
            from app.pipeline.enrichment.area import PriceGrowthExtract

            return PriceGrowthExtract(result_index=None, pct=None, evidence=None, confidence=0)
        if kwargs["task"] == "summarize_area":
            from app.pipeline.enrichment.area import AreaSummary

            return AreaSummary(
                summary="A fake area summary.", infrastructure_summary="A fake transport note."
            )
        if kwargs["task"] == "explain_recommendation":
            from app.pipeline.ranking import Explanation

            return Explanation(
                reason="A fake explanation without numbers.",
                highlights=["Fits the profile"],
                risks=["Not a verified unit"],
            )
        if kwargs["task"] == "extract_price_level":
            from app.pipeline.enrichment.price_level import PriceLevelExtract

            return PriceLevelExtract(
                result_index=None, low=None, high=None, evidence=None, confidence=0
            )
        if kwargs["task"] == "review_development":
            from app.pipeline.enrichment.development import DevelopmentReview

            return DevelopmentReview(review="inconclusive", hypotheses=[])
        return self.extraction if kwargs["task"] == "extract_listing" else self.assessment


def candidate(**overrides):
    source = SourceRef(engine=SerpEngine.GOOGLE, url="https://www.99acres.com/example")

    def fact(value):
        return Sourced(
            value=value,
            confidence=0.8 if value is not None else 0,
            method=ExtractionMethod.REGEX,
            sources=[source],
        )

    now = datetime.now(UTC)
    return Listing.model_validate(
        {
            "id": "candidate-1",
            "kind": ResultKind.SNIPPET_ENTRY,
            "portal": Portal.NINETY_NINE_ACRES,
            "name": "Example apartment",
            "segment": "residential",
            "url": source.url,
            "property_type": fact("apartment"),
            "locality": fact("whitefield"),
            "price_inr": fact(6_000_000),
            "price_per_sqft": fact(None),
            "size_sqft": fact(1000),
            "bedrooms": fact(None),
            "status": fact(None),
            "location": fact(None),
            "evidence": (
                "Apartment for sale at Rs 60 lakh. 1000 sqft. Three bedrooms, ready to move."
            ),
            "sources": [source],
            "first_seen_at": now,
            "last_seen_at": now,
            **overrides,
        }
    )


def context(llm=None, **profile):
    now = datetime.now(UTC)
    return SimpleNamespace(
        profile=InvestorProfile(
            id="profile-1", created_at=now, updated_at=now, **(RESIDENTIAL | profile)
        ),
        llm=llm or FakeLLM(),
    )


def test_extraction_only_adds_supported_missing_fields():
    listing = candidate()
    llm = FakeLLM()
    llm.extraction.status.value = "ready_to_move"
    llm.extraction.status.confidence = 0.9
    llm.extraction.status.evidence = "ready to move"
    llm.extraction.price_inr.value = "1"
    llm.extraction.price_inr.confidence = 1
    llm.extraction.price_inr.evidence = "Rs 60 lakh"
    updated = extract(context(llm), listing)
    assert updated.status.value == "ready_to_move"
    assert updated.status.method == ExtractionMethod.LLM
    assert updated.status.sources == listing.sources
    assert "ready to move" in updated.status.note
    assert updated.price_inr == listing.price_inr
    assert listing.status.value is None  # no mutation of the cleaning result
    assert updated.price_per_sqft.value == 6000
    assert llm.calls[0]["tier"] == ModelTier.LITE


@pytest.mark.parametrize("evidence", ["invented text", "", None])
def test_unsupported_extraction_does_not_fill_gaps(evidence):
    llm = FakeLLM()
    llm.extraction.bedrooms.value = "3"
    llm.extraction.bedrooms.confidence = 0.9
    llm.extraction.bedrooms.evidence = evidence
    assert extract(context(llm), candidate()).bedrooms.value is None


def test_no_evidence_or_no_missing_fields_skips_extraction():
    llm = FakeLLM()
    assert extract(context(llm), candidate(evidence=None)).status.value is None
    listing = candidate()
    listing.bedrooms.value = 3
    listing.status.value = "ready_to_move"
    extract(context(llm), listing)
    assert not llm.calls


@pytest.mark.parametrize(
    "field,value,evidence,expected",
    [
        ("price_inr", "12000000", "Rs 1.2 Cr", 12_000_000),
        ("price_inr", "8500000", "INR 8,500,000", 8_500_000),
        ("price_inr", "8500000", "Rs 1.2 Cr", None),
        ("price_inr", "300000", "Rs 60 lakh, 3 BHK", None),
        ("price_inr", "45000", "Rs 45,000/month", None),
        ("price_inr", "45000", "Monthly rent INR 45,000", None),
        ("price_inr", "6000000", "average price Rs 60 lakh", None),
        ("price_inr", "6000000", "under Rs 60 lakh", None),
        ("price_inr", "6000000", "Rs 60-70 lakh", None),
        ("price_inr", "6000000", "Rs 60 to 70 lakh", None),
        ("price_inr", "10", "$10", None),
        ("price_inr", "NaN", "Rs 60 lakh", None),
        ("price_inr", "Infinity", "Rs 60 lakh", None),
        ("price_inr", "-1", "Rs 60 lakh", None),
        ("size_sqft", "731.95", "68 sqm", 731.95),
        ("size_sqft", "900", "100 sq yd", 900),
        ("size_sqft", "1000", "1000 sqft", 1000),
        ("size_sqft", "1000", "100 sqm", None),
        ("size_sqft", "1000", "1000 to 2000 sqft", None),
        ("bedrooms", "3", "3 BHK", 3),
        ("bedrooms", "3", "2 and 3 bedroom", None),
        ("bedrooms", "2.5", "2 BHK", None),
        ("property_type", "office", "Office Space", "office"),
        ("property_type", "apartment", "Office Space", None),
        ("status", "new_launch", "New launch", "new_launch"),
        ("status", "new_launch", "Ready to move", None),
    ],
)
def test_values_must_agree_with_evidence(field, value, evidence, expected):
    assert _supported_value(field, value, evidence) == expected


@pytest.mark.parametrize(
    "change,profile,reason",
    [
        ({"price_inr": 8_000_001}, {}, "maximum budget"),
        ({"price_inr": 5_000_000}, {"budget_min_inr": 5_500_000}, "minimum budget"),
        ({"size_sqft": 999}, {"size_min_sqft": 1000}, "minimum size"),
        ({"size_sqft": 1001}, {"size_max_sqft": 1000}, "maximum size"),
        ({"property_type": PropertyType.HOUSE_VILLA}, {}, "Property type"),
        ({"locality": "hebbal"}, {}, "Locality"),
    ],
)
def test_hard_mismatch_overrides_model_strong_match(change, profile, reason):
    listing = candidate()
    for name, value in change.items():
        getattr(listing, name).value = value
    result = verify(context(**profile), listing)
    assert result.verdict == MatchVerdict.REJECT
    assert result.match_score <= 39
    assert any(reason in mismatch for mismatch in result.mismatches)
    assert not result.matched_criteria
    assert result.listing_id == listing.id and result.model == "fake-reasoning"


def test_boundary_values_are_inclusive():
    result = verify(
        context(
            budget_min_inr=6_000_000,
            budget_max_inr=6_000_000,
            size_min_sqft=1000,
            size_max_sqft=1000,
        ),
        candidate(),
    )
    assert result.verdict == MatchVerdict.STRONG


@pytest.mark.parametrize("field", ["price_inr", "size_sqft", "property_type", "locality"])
def test_missing_facts_are_uncertain_not_rejected(field):
    listing = candidate()
    getattr(listing, field).value = None
    result = verify(context(), listing)
    assert result.verdict == MatchVerdict.PARTIAL
    assert result.match_score <= 69 and result.confidence <= 0.6
    assert not result.mismatches
    assert any("missing" in message.lower() for message in result.missing_data)


def test_roi_is_not_claimed_verified():
    result = verify(context(), candidate())
    assert any("Target ROI" in reason for reason in result.missing_data)


def test_starting_price_does_not_confirm_budget_or_violate_minimum():
    listing = candidate()
    listing.price_inr.note = "starting price"
    result = verify(context(budget_min_inr=7_000_000), listing)
    assert result.verdict == MatchVerdict.PARTIAL
    assert not result.mismatches
    assert any("Final unit price" in reason for reason in result.missing_data)


def test_identity_and_timestamps_do_not_change_prompts():
    listing = candidate()
    first = prompt_for("extract_listing", listing=listing_input(listing))
    listing.last_seen_at = datetime(2027, 1, 1, tzinfo=UTC)
    assert prompt_for("extract_listing", listing=listing_input(listing)) == first


def test_prompt_files_have_no_bom_and_prompts_ignore_one(tmp_path, monkeypatch):
    # A BOM would silently change every prompt and so every LLM cache key and fixture.
    for path in PROMPTS.glob("*.md"):
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name
    (tmp_path / "task.md").write_text("\ufeffPrompt", encoding="utf-8")
    monkeypatch.setattr("app.pipeline.verification.PROMPTS", tmp_path)
    assert prompt_for("task").startswith("Prompt")


def test_implausibly_cheap_candidate_is_kept_but_capped_at_weak():
    from tests.unit.test_quality import BENCHMARK

    listing = candidate()
    listing.price_inr.value, listing.size_sqft.value = 360_000, 4_800
    result = verify(context(), listing, BENCHMARK)
    assert result.verdict == MatchVerdict.WEAK and result.match_score <= 59
    assert any("monthly rent" in reason for reason in result.mismatches)
    assert verify(context(), candidate(), BENCHMARK).verdict == MatchVerdict.STRONG
