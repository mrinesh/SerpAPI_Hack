"""F-09 search inputs. Shared cohort quotes, validated in code, never model arithmetic."""

import re

from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.integrations.llm.base import ModelTier
from app.integrations.serpapi import engines
from app.pipeline.cleaning import normalize_text
from app.pipeline.context import PipelineContext
from app.pipeline.metrics import derived, missing
from app.pipeline.query_planner import QUERY_WORDS
from app.pipeline.verification import prompt_for
from app.reference import Market
from app.schemas.common import SerpEngine
from app.schemas.listing import Listing
from app.schemas.profile import PropertyType
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef

COMMERCIAL = {PropertyType.OFFICE, PropertyType.SHOP_SHOWROOM, PropertyType.WAREHOUSE}
TYPE_WORDS = {
    PropertyType.APARTMENT: r"\b(?:flat|apartment)s?\b",
    PropertyType.HOUSE_VILLA: r"\b(?:independent house|villa)s?\b",
    PropertyType.BUILDER_FLOOR: r"\bbuilder floor\b",
    PropertyType.OFFICE: r"\boffice(?: space)?s?\b",
    PropertyType.SHOP_SHOWROOM: r"\b(?:shop|showroom)s?\b",
    PropertyType.WAREHOUSE: r"\b(?:warehouse|godown)s?\b",
}
MONTH = re.compile(r"(?:per|/)\s*(?:month|mo\b)|\bmonthly\b", re.I)
SQFT = re.compile(r"(?:per|/)\s*sq[.\s-]*f(?:ee)?t", re.I)
UNIT_AREA = re.compile(r"\b([\d,]+(?:\.\d+)?)\s*sq[.\s-]*f(?:ee)?t\b", re.I)
MONEY = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore|cr\b|k\b)?", re.I)
BOUND = re.compile(r"starting|starts|onwards|\bfrom\b|\bto\b|\d\s*[-\u2013]\s*(?:₹|rs|\d)", re.I)
ANNUAL = re.compile(
    r"year[- ]on[- ]year|\byoy\b|(?:past|last)\s+(?:12\s*months|one year|1 year|year)", re.I
)


class QuoteSelection(BaseModel):
    result_index: int | None
    evidence: str | None
    confidence: float = Field(ge=0, le=1)


def cohort(listing: Listing) -> tuple[str, PropertyType, int | None] | None:
    kind = listing.property_type.value
    if not listing.locality.value or kind not in TYPE_WORDS:
        return None
    if kind in COMMERCIAL:
        if not listing.size_sqft.value or listing.size_sqft.value <= 0:
            return None
        return listing.locality.value, kind, None
    if not listing.bedrooms.value or listing.bedrooms.value <= 0:
        if listing.size_sqft.value and listing.size_sqft.value > 0:
            return listing.locality.value, kind, None  # indicative per-area rental quote
        return None
    return listing.locality.value, kind, listing.bedrooms.value


def supported_rent(evidence: str, kind: PropertyType, bedrooms: int | None) -> float | None:
    """One INR monthly quote; commercial requires a per-sq-ft rate, housing exact BHK."""
    if not MONTH.search(evidence) or BOUND.search(evidence):
        return None
    if re.search(r"(?:per|/)\s*(?:person|seat|desk)|co[- ]?working|virtual office", evidence, re.I):
        return None
    if not re.search(TYPE_WORDS[kind], evidence, re.I):
        return None
    area = None
    if kind in COMMERCIAL or bedrooms is None:
        if not SQFT.search(evidence):
            sizes = UNIT_AREA.findall(evidence)
            if kind not in COMMERCIAL or len(sizes) != 1:
                return None
            area = float(sizes[0].replace(",", ""))
            if area <= 0:
                return None
    elif SQFT.search(evidence) or set(re.findall(r"\b(\d+)\s*bhk\b", evidence, re.I)) != {
        str(bedrooms)
    }:
        return None
    matches = list(MONEY.finditer(evidence))
    if len(matches) != 1:
        return None
    quote = matches[0]
    scale = {"lakh": 100000, "lac": 100000, "crore": 10000000, "cr": 10000000, "k": 1000}
    amount = float(quote[1].replace(",", "")) * scale.get((quote[2] or "").lower(), 1)
    if re.search(r"deposit\s*(?:of|amount|:)?\s*(?:₹|rs|inr)", evidence, re.I):
        return None
    return (amount / area if area else amount) if amount > 0 else None


def supported_growth(evidence: str) -> float | None:
    """Reject forecasts, other periods and unsigned declines; preserve negative annual growth."""
    if not ANNUAL.search(evidence) or re.search(
        r"forecast|expect|projected|next|rental|yield", evidence, re.I
    ):
        return None
    numbers = re.findall(r"(?<![\d.])([+-]?\d+(?:\.\d+)?)\s*%", evidence)
    if len(numbers) != 1:
        return None
    value = float(numbers[0])
    if re.search(r"fell|fall|declin|decreas|drop", evidence, re.I):
        value = -abs(value)
    elif value >= 0 and not re.search(
        r"increas|grew|growth|rose|rise|risen|appreciat|gain|changed?\s+by", evidence, re.I
    ):
        return None
    return value if -100 <= value <= 100 else None


class InvestmentInputs:
    """Per-run memoization over raw gateway caches. At most one lookup per cohort/type."""

    def __init__(self, ctx: PipelineContext, market: Market):
        self.ctx, self.market = ctx, market
        self.rents: dict[tuple, Sourced] = {}
        self.growths: dict[tuple, Sourced] = {}
        self.warnings: list[str] = []

    def rent(self, listing: Listing) -> Sourced[int]:
        key = cohort(listing)
        if key is None:
            return missing(
                "Rent unavailable: need supported type and BHK (housing) or size (commercial)"
            )
        slug, kind, bedrooms = key
        place = self.market.locality(slug)
        if place is None:
            return missing("Unknown rent locality")
        if key not in self.rents:
            unit = f"{bedrooms} BHK " if bedrooms else ""
            rate = " per sq ft" if bedrooms is None else ""
            query = (
                f"{unit}{QUERY_WORDS[kind]} monthly rent{rate} in "
                f"{place.name} {self.market.query_city_name}"
            )
            self.rents[key] = self._quote("extract_rent", query, place.name, kind, bedrooms)
        rent = self.rents[key]
        if bedrooms is None:
            result = derived(
                [rent, listing.size_sqft],
                lambda r, s: r * s,
                "Indicative rent rate * unit size; layout/fit-out/lease terms may differ",
            )
            return Sourced[int].model_validate(
                result.model_copy(
                    update={"value": round(result.value) if result.value is not None else None}
                ).model_dump()
            )
        return Sourced[int].model_validate(rent.model_dump())

    def growth(self, listing: Listing) -> Sourced[float]:
        if self.ctx.profile.expected_growth_pct is not None:
            return missing("Investor override supplied; no growth search needed")
        slug, kind = listing.locality.value, listing.property_type.value
        return self.observed_growth(slug, kind)

    def observed_growth(self, slug: str | None, kind: PropertyType | None) -> Sourced[float]:
        """Measured history for area research; an investor assumption never replaces evidence."""
        if not slug or kind not in TYPE_WORDS:
            return missing("No supported same-type annual price growth input")
        key = slug, kind
        if key not in self.growths:
            place = self.market.locality(slug)
            if place is None:
                return missing("Unknown growth locality")
            query = (
                f"{QUERY_WORDS[kind]} property prices past 12 months growth in "
                f"{place.name} {self.market.query_city_name}"
            )
            self.growths[key] = self._quote("extract_growth", query, place.name, kind, None)
        return self.growths[key]

    def _quote(self, task, query, locality, kind, bedrooms) -> Sourced:
        try:
            response = self.ctx.serp.search(
                *engines.google_search(query, self.ctx.settings), run_id=self.ctx.run_id
            )
            results = [
                {
                    "index": i,
                    "title": r.get("title", ""),
                    "link": r.get("link"),
                    "snippet": r["snippet"],
                    "date": r.get("date"),
                }
                for i, r in enumerate(response.data.get("organic_results", [])[:8])
                if r.get("snippet") and r.get("link")
            ]
            if task == "extract_rent":
                # Screen units/amounts before asking the model to choose. Otherwise it can
                # favour a bare per-sq-ft quote and silently assume a monthly billing period.
                results = [
                    r for r in results if supported_rent(r["snippet"], kind, bedrooms) is not None
                ]
            if not results:
                return missing(f"No search evidence for {task}")
            selection = self.ctx.llm.generate_structured(
                task=task,
                prompt=prompt_for(
                    task,
                    locality=locality,
                    property_type=QUERY_WORDS[kind],
                    bedrooms=bedrooms,
                    results=results,
                ),
                schema=QuoteSelection,
                tier=ModelTier.LITE,
            )
        except AppError as exc:
            note = f"{task} in {locality}: {exc.code}: {exc.message}"
            self.warnings.append(note)
            return missing(note)
        chosen = next((r for r in results if r["index"] == selection.result_index), None)
        quote = normalize_text(selection.evidence or "")
        # Full evidence must occur verbatim in one snippet, including locality and type.
        if not chosen or not quote or selection.confidence <= 0:
            return missing(f"No comparable grounded quote for {task}")
        text = normalize_text(chosen["snippet"])
        if task == "extract_rent" and quote != text:
            return missing(
                "Rent quote must preserve the complete snippet, including units and qualifiers"
            )
        if re.search(re.escape(locality) + r"\s+(?:extension|outskirts)\b", quote, re.I):
            return missing(f"{task}: neighbouring locality is not a comparable")
        if quote not in text or not re.search(
            r"(?<!\w)" + re.escape(locality) + r"(?!\w)", quote, re.I
        ):
            return missing(f"{task}: quote not supported by exact locality evidence")
        if not re.search(TYPE_WORDS[kind], quote, re.I):
            return missing(f"{task}: property type not supported by evidence")
        if task == "extract_growth" and re.search(r"forecast|expected|projected|next", text, re.I):
            return missing(
                "Growth source contains forecast qualifiers; cannot treat it as observed change"
            )
        value = (
            supported_rent(quote, kind, bedrooms)
            if task == "extract_rent"
            else supported_growth(quote)
        )
        if value is None:
            return missing(
                f"{task}: quote has ambiguous units, amount, comparability or annual period"
            )
        # A housing quote for a whole unit must be in whole rupees.
        if task == "extract_rent" and bedrooms is not None:
            value = round(value)
        source = SourceRef(
            engine=SerpEngine.GOOGLE,
            url=chosen["link"],
            title=chosen["title"],
            search_id=response.search_id,
        )
        return Sourced(
            value=value,
            confidence=min(selection.confidence, 0.6),
            method=(
                ExtractionMethod.COMPUTED
                if task == "extract_rent" and kind in COMMERCIAL and not SQFT.search(quote)
                else ExtractionMethod.LLM
            ),
            sources=[source],
            note=(
                f'Asking rent (same locality/type; indicative, not achieved rent): "{quote}"; '
                + (
                    "unit monthly rent divided by quoted sq ft to obtain rate"
                    if kind in COMMERCIAL and not SQFT.search(quote)
                    else "quoted rate or BHK rent"
                )
            )
            if task == "extract_rent"
            else (
                f'Reported past annual change, not a forecast: "{quote}"; '
                f"result date: {chosen['date'] or 'not supplied'}"
            ),
        )
