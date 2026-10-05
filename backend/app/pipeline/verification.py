"""DeepSeek extraction and profile relevance checks (F-03).

Only missing facts with a supporting span may be added. Hard constraints are checked in code;
model scores describe relevance, never investment returns or the later composite ranking.
"""

import json
import math
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import BaseModel, Field

from app.integrations.llm.base import ModelTier
from app.pipeline.cleaning import normalize_text, parse_property_type, parse_status
from app.pipeline.context import PipelineContext
from app.schemas.listing import Listing, MatchVerdict, SaleStatus, Verification
from app.schemas.profile import SEGMENT_PROPERTY_TYPES, PropertyType, Segment
from app.schemas.provenance import ExtractionMethod, Sourced

PROMPTS = Path(__file__).resolve().parents[1] / "integrations" / "llm" / "prompts"
EXTRACT_FIELDS = ("property_type", "price_inr", "size_sqft", "bedrooms", "status")
# Gaps in these cap confidence and block a strong verdict.
CORE_FACTS = (
    ("price_inr", "Asking price is missing; budget cannot be confirmed."),
    ("size_sqft", "Property size is missing."),
    ("property_type", "Property type is missing."),
    ("locality", "Locality is missing."),
)
PRICE_UNCONFIRMED = (
    "Final unit price is unconfirmed; the quoted price is a range or starting price."
)
# Always noted, never a cap: ROI is unknowable until investment metrics exist (F-09).
ROI_UNVERIFIED = "Target ROI requires investment metrics; it is not verified at this stage."


class ExtractedField(BaseModel):
    value: str | None
    confidence: float = Field(ge=0, le=1)
    evidence: str | None  # exact span from this candidate's evidence, not its search-page title


class ExtractedListing(BaseModel):
    property_type: ExtractedField
    price_inr: ExtractedField
    size_sqft: ExtractedField
    bedrooms: ExtractedField
    status: ExtractedField


class VerificationAssessment(BaseModel):
    """Model output; identity and model attribution are supplied by the application."""

    match_score: int = Field(ge=0, le=100)
    verdict: MatchVerdict
    matched_criteria: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


def listing_input(listing: Listing) -> dict:
    # Timestamps change every run, but are irrelevant to extraction and verification.
    return listing.model_dump(mode="json", exclude={"first_seen_at", "last_seen_at"})


def prompt_for(task: str, **inputs: object) -> str:
    # utf-8-sig drops an editor BOM, which would otherwise enter the prompt and the cache key.
    prompt = (PROMPTS / f"{task}.md").read_text(encoding="utf-8-sig").strip()
    return prompt + "\n\nINPUT JSON:\n" + json.dumps(inputs, sort_keys=True, ensure_ascii=False)


def extract(ctx: PipelineContext, listing: Listing) -> Listing:
    missing = [field for field in EXTRACT_FIELDS if getattr(listing, field).value is None]
    if not missing or not listing.evidence or not listing.sources:
        return listing
    output = ctx.llm.generate_structured(
        task="extract_listing",
        prompt=prompt_for(
            "extract_listing", listing=listing_input(listing), missing_fields=missing
        ),
        schema=ExtractedListing,
        tier=ModelTier.LITE,
    )
    result = listing.model_copy(deep=True)
    for name in missing:
        field = getattr(output, name)
        if (
            field.value is None
            or field.confidence <= 0
            or not field.evidence
            or field.evidence not in listing.evidence
        ):
            continue
        value = _supported_value(name, field.value, field.evidence)
        if value is None:
            continue
        setattr(
            result,
            name,
            Sourced(
                value=value,
                confidence=field.confidence,
                method=ExtractionMethod.LLM,
                sources=listing.sources,
                note=f'Evidence: "{field.evidence}"',
            ),
        )
    if result.price_per_sqft.value is None and result.price_inr.value and result.size_sqft.value:
        result.price_per_sqft = Sourced(
            value=round(result.price_inr.value / result.size_sqft.value, 2),
            confidence=min(result.price_inr.confidence, result.size_sqft.confidence, 0.6),
            method=ExtractionMethod.COMPUTED,
            sources=listing.sources,
            note="price / size",
        )
    # Validate constructed generic fields against the concrete Listing types.
    return Listing.model_validate(result.model_dump())


def _supported_value(name: str, raw: str, evidence: str):
    """Reject invented values, wrong units, rental amounts, ranges and statistical summaries."""
    text = normalize_text(evidence)
    try:
        if name == "property_type":
            value = PropertyType(raw)
            segment = next(s for s in Segment if value in SEGMENT_PROPERTY_TYPES[s])
            return value if parse_property_type(text, segment) == value else None
        if name == "status":
            value = SaleStatus(raw)
            return value if parse_status(text) == value else None
        value = Decimal(raw)
    except (ValueError, InvalidOperation):
        return None
    if not value.is_finite() or value <= 0:
        return None
    if name in {"price_inr", "bedrooms"} and value != value.to_integral_value():
        return None
    if name == "price_inr":
        if re.search(
            r"rent|/\s*(?:m\b|month)|per\s+month|monthly|emi|average|median|between|"
            r"budget|under|below|upto|up to|starting|\bfrom\b",
            text,
            re.I,
        ):
            return None
        if re.search(r"\d\s*(?:-|to)\s*\d", text, re.I):
            return None
        prices = re.finditer(
            r"(?P<currency>₹|\binr\b|\brs\.?)?\s*"
            r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*"
            r"(?P<unit>lacs?\b|lakhs?\b|crores?\b|cr\b)?",
            text,
            re.I,
        )
        for price in prices:
            if not price["currency"] and not price["unit"]:
                continue
            unit = (price["unit"] or "").lower()
            multiplier = 10_000_000 if unit.startswith("cr") else 100_000 if unit else 1
            if Decimal(price["number"].replace(",", "")) * multiplier == value:
                return int(value)
        return None
    if name == "size_sqft":
        if re.search(r"\d\s*(?:-|to)\s*\d|ranging|between", text, re.I):
            return None
        for number, unit in re.findall(
            r"(\d[\d,]*(?:\.\d+)?)\s*(sq\.?\s*ft\.?|sqft|sq\.?\s*m\b|sqm|sq\.?\s*yd|sqyd)",
            text,
            re.I,
        ):
            multiplier = 10.7639 if "m" in unit.lower() else 9 if "yd" in unit.lower() else 1
            supported = float(Decimal(number.replace(",", ""))) * multiplier
            if math.isclose(float(value), supported, abs_tol=0.1):
                return float(value)
        return None
    if name == "bedrooms":
        if re.search(r"\d\s*(?:,|and|to|-|/)\s*\d", text, re.I):
            return None
        match = re.search(r"(\d+)\s*(?:bhk|bedrooms?)", text, re.I)
        return int(value) if match and int(match[1]) == value else None
    return None


def verify(ctx: PipelineContext, listing: Listing) -> Verification:
    profile = ctx.profile.model_dump(
        mode="json", exclude={"id", "name", "created_at", "updated_at"}
    )
    assessment = ctx.llm.generate_structured(
        task="verify_listing",
        prompt=prompt_for("verify_listing", profile=profile, listing=listing_input(listing)),
        schema=VerificationAssessment,
        tier=ModelTier.REASONING,
    )
    result = Verification(
        listing_id=listing.id,
        model=ctx.llm.model_for(ModelTier.REASONING),
        **assessment.model_dump(),
    )
    hard_mismatches: list[str] = []
    if listing.segment != ctx.profile.segment:
        hard_mismatches.append("Property segment does not match the profile.")
    kind = listing.property_type.value
    if kind is not None and kind not in ctx.profile.property_types:
        hard_mismatches.append("Property type does not match the selected types.")
    locality = listing.locality.value
    if locality is not None and locality not in ctx.profile.localities:
        hard_mismatches.append("Locality is outside the selected localities.")
    price = listing.price_inr.value
    price_is_bound = bool(
        listing.price_inr.note
        and re.search(r"range|starting price|lower bound", listing.price_inr.note, re.I)
    )
    if price is not None:
        if price > ctx.profile.budget_max_inr:
            hard_mismatches.append("Quoted price exceeds the maximum budget.")
        if (
            not price_is_bound
            and ctx.profile.budget_min_inr is not None
            and price < ctx.profile.budget_min_inr
        ):
            hard_mismatches.append("Quoted price is below the minimum budget.")
    size = listing.size_sqft.value
    if size is not None:
        if ctx.profile.size_min_sqft is not None and size < ctx.profile.size_min_sqft:
            hard_mismatches.append("Property size is below the minimum size.")
        if ctx.profile.size_max_sqft is not None and size > ctx.profile.size_max_sqft:
            hard_mismatches.append("Property size exceeds the maximum size.")
    gaps = [label for field, label in CORE_FACTS if getattr(listing, field).value is None]
    uncertain = bool(gaps) or price_is_bound
    notes = [*gaps, *([PRICE_UNCONFIRMED] if price_is_bound else []), ROI_UNVERIFIED]
    result.missing_data = list(dict.fromkeys([*result.missing_data, *notes]))
    result.mismatches = list(dict.fromkeys([*result.mismatches, *hard_mismatches]))
    if hard_mismatches:
        result.verdict = MatchVerdict.REJECT
        result.match_score = min(result.match_score, 39)
        # Do not display model claims of matching criteria alongside contradictory constraints.
        result.matched_criteria = []
    elif result.verdict is MatchVerdict.REJECT and not result.mismatches:
        # Missing evidence is uncertainty, not a confirmed failure of the criteria.
        result.verdict = MatchVerdict.WEAK
    if uncertain:
        result.confidence = min(result.confidence, 0.6)
        result.match_score = min(result.match_score, 69)
        if result.verdict is MatchVerdict.STRONG:
            result.verdict = MatchVerdict.PARTIAL
    if result.verdict is MatchVerdict.REJECT:
        result.match_score = min(result.match_score, 39)
    return result
