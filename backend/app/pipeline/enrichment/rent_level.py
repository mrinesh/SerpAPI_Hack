"""Locality rent level per sq ft per month, the input for rental yield (F-09, ADR 0017).

One Google search per locality and property type, e.g. "flat rent per sq ft in Whitefield
Bangalore". Rent results quote a monthly rent next to a size ("₹38,000 / month … 850 sqft"),
rarely a rate, so DeepSeek (lite, prompt `extract_rent`) lists the rent and size pairs it sees
with the exact span of each. Code checks every pair against its snippet, computes rent ÷ size,
and takes the median of at least `MIN_PAIRS`. No benchmark is invented: too few pairs means no
rent level, and so no rental yield.
"""

import re
import statistics

from pydantic import BaseModel, Field

from app.config import Settings
from app.integrations.llm.base import ModelTier
from app.integrations.serpapi import engines
from app.integrations.serpapi.engines import EngineCall
from app.pipeline.cleaning import normalize_text
from app.pipeline.context import PipelineContext
from app.pipeline.query_planner import QUERY_WORDS
from app.pipeline.verification import prompt_for
from app.reference import Market
from app.schemas.common import SerpEngine
from app.schemas.profile import PropertyType
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef

MAX_RESULTS = 8
MIN_PAIRS = 3
# Recorded traps: "₹6,000 / month 10,000 sqft Plot area"; coworking seats. A span may mention a
# deposit ("₹38,000 / month + Deposit 2 months rent 850 sqft"): the quoted rent is still monthly.
_NOT_A_UNIT = re.compile(r"plot|seat|desk|per\s+day|coworking", re.I)
_SIZE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:sq\.?\s*-?\s*f(?:ee)?t|sqft)", re.I)
_RUPEES = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(lacs?\b|lakhs?\b|l\b|k\b|cr\b|crores?\b)?", re.I)


class RentPair(BaseModel):
    result_index: int
    monthly_rent: float = Field(gt=0)
    size_sqft: float = Field(gt=0)
    evidence: str


class RentExtract(BaseModel):
    """Output schema of the `extract_rent` prompt."""

    pairs: list[RentPair] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


def rent_call(
    name: str, property_type: PropertyType, market: Market, settings: Settings
) -> EngineCall:
    return engines.google_search(
        f"{QUERY_WORDS[property_type]} rent per sq ft in {name} {market.query_city_name}", settings
    )


def rupee_amounts(text: str) -> set[float]:
    """Every amount the text could mean: "₹1.7 Lac" -> 170000, "35k" -> 35000, "45,000"."""
    amounts = set()
    for match in _RUPEES.finditer(text):
        number = float(match.group(1).replace(",", ""))
        unit = (match.group(2) or "").lower()
        multiplier = (
            10_000_000 if unit.startswith("cr")
            else 100_000 if unit.startswith("la") or unit == "l"
            else 1_000 if unit == "k"
            else 1
        )  # fmt: skip
        amounts.add(number * multiplier)
    return amounts


def supported_rate(pair: RentPair, snippet: str, title: str = "") -> float | None:
    """Rent per sq ft per month when the span is in the snippet, quotes both the rent and the
    size, and is a whole-unit rent in a rent listing; otherwise None."""
    span, text = normalize_text(pair.evidence), normalize_text(snippet)
    if span not in text or _NOT_A_UNIT.search(span):
        return None
    if not re.search(r"rent|lease|/\s*month|per\s+month", f"{title} {text}", re.I):
        return None
    sizes = {float(size.replace(",", "")) for size in _SIZE.findall(span)}
    if pair.size_sqft not in sizes or pair.monthly_rent not in rupee_amounts(span):
        return None
    if pair.monthly_rent == pair.size_sqft:
        return None  # the same number read twice
    return pair.monthly_rent / pair.size_sqft


def median_rate(extract: RentExtract, results: list[dict]) -> tuple[float, list[dict], int] | None:
    """The median checked rate, the results it came from, and how many pairs passed."""
    by_index = {result["index"]: result for result in results}
    rates, used = [], []
    for pair in extract.pairs:
        result = by_index.get(pair.result_index)
        rate = (
            supported_rate(pair, result["snippet"], result.get("title") or "") if result else None
        )
        if rate is not None:
            rates.append(rate)
            if result not in used:
                used.append(result)
    if len(rates) < MIN_PAIRS:
        return None
    return round(statistics.median(rates), 1), used, len(rates)


def rent_level(
    ctx: PipelineContext, market: Market, name: str, property_type: PropertyType
) -> Sourced[float] | None:
    """None when the results hold too few checked pairs; raises AppError when a provider fails,
    so the caller can record the failure (ADR 0019)."""
    response = ctx.serp.search(
        *rent_call(name, property_type, market, ctx.settings), run_id=ctx.run_id
    )
    results = [
        {"index": i, "title": r.get("title"), "link": r.get("link"), "snippet": snippet}
        for i, r in enumerate(response.data.get("organic_results", [])[:MAX_RESULTS])
        if (snippet := r.get("snippet"))
    ]
    if not results:
        return None
    extract = ctx.llm.generate_structured(
        task="extract_rent",
        prompt=prompt_for(
            "extract_rent",
            locality=name,
            property_type=QUERY_WORDS[property_type],
            results=results,
        ),
        schema=RentExtract,
        tier=ModelTier.LITE,
    )
    found = median_rate(extract, results)
    if found is None:
        return None
    rate, used, checked = found
    return Sourced(
        value=rate,
        confidence=min(extract.confidence, 0.6),
        method=ExtractionMethod.LLM,
        sources=[
            SourceRef(
                engine=SerpEngine.GOOGLE,
                url=result["link"],
                title=result["title"],
                search_id=response.search_id,
            )
            for result in used
        ],
        note=(
            f"Median of {checked} quoted rents ÷ sizes, per sq ft per "
            "month; listed rents can include maintenance or furnishing"
        ),
    )
