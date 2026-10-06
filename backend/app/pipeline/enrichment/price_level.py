"""Locality price level per sq ft, the benchmark for price flags (F-05 price level, F-12, ADR 0014).

One Google search per locality and property type, e.g. "office space price per sq ft in
Koramangala Bangalore". DeepSeek (lite) picks a quoted sale rate and the exact span it came from;
code checks the span and the numbers, then takes the midpoint of a range. When the search gives
no usable rate, the median of at least `MIN_PEERS` rates quoted in this run is used instead.
There is no flat fallback rate: no benchmark means no price flag.

Repeat runs are free: the SerpApi cache and the LLM cache both key on the exact request.
"""

import re
import statistics

from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.integrations.llm.base import ModelTier
from app.integrations.serpapi import engines
from app.pipeline.cleaning import normalize_text
from app.pipeline.context import PipelineContext
from app.pipeline.query_planner import QUERY_WORDS
from app.pipeline.verification import prompt_for
from app.reference import Market
from app.schemas.common import SerpEngine
from app.schemas.listing import Listing
from app.schemas.profile import PropertyType
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef

MAX_RESULTS = 8  # organic results shown to the model
MIN_PEERS = 3  # quoted rates needed before the run's median is trusted
_RENT = re.compile(r"rent|lease|/\s*(?:m\b|month)|per\s+month|monthly|yield|emi", re.I)
_SQFT = re.compile(r"sq[.\s-]*f(?:ee)?t|per\s+sq", re.I)  # sq ft, sqft, Sq-ft, sq. feet
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

LevelKey = tuple[str, PropertyType]  # (locality slug, property type)


class PriceLevelExtract(BaseModel):
    """Output schema of the `extract_price_level` prompt."""

    result_index: int | None
    low: float | None
    high: float | None
    evidence: str | None
    confidence: float = Field(ge=0, le=1)


def price_levels(
    ctx: PipelineContext, market: Market, listings: list[Listing]
) -> tuple[dict[LevelKey, Sourced[float]], list[str]]:
    """Benchmarks for every (locality, profile property type) among `listings`, plus one
    progress note per key saying where its number came from."""
    keys = sorted(
        {
            (listing.locality.value, listing.property_type.value)
            for listing in listings
            if listing.locality.value and listing.property_type.value in ctx.profile.property_types
        }
    )
    levels: dict[LevelKey, Sourced[float]] = {}
    notes: list[str] = []
    for locality, property_type in keys:
        place = market.locality(locality)
        name = place.name if place else locality
        level = _searched_level(ctx, market, name, property_type)
        if level is None:
            level = peer_median(listings, locality, property_type)
        if level is None:
            notes.append(f"No price level for {QUERY_WORDS[property_type]} in {name}")
            continue
        levels[(locality, property_type)] = level
        origin = "search" if level.method is ExtractionMethod.LLM else "this run's quotes"
        notes.append(
            f"{QUERY_WORDS[property_type]} in {name}: ₹{level.value:,.0f}/sq ft ({origin})"
        )
    return levels, notes


def peer_median(
    listings: list[Listing], locality: str, property_type: PropertyType
) -> Sourced[float] | None:
    """Median of per-sq-ft rates quoted on portal pages (not computed) for the same key."""
    peers = [
        listing
        for listing in listings
        if listing.locality.value == locality
        and listing.property_type.value == property_type
        and listing.price_per_sqft.value
        and listing.price_per_sqft.method is ExtractionMethod.REGEX
    ]
    if len(peers) < MIN_PEERS:
        return None
    return Sourced(
        value=float(statistics.median(p.price_per_sqft.value for p in peers)),
        confidence=0.5,
        method=ExtractionMethod.COMPUTED,
        sources=[source for p in peers for source in p.sources],
        note=f"median of {len(peers)} rates quoted in this run",
    )


def supported_rate(extract: PriceLevelExtract, snippet: str) -> float | None:
    """The midpoint rate when the span is in the snippet, quotes every number returned, is per
    sq ft and is not a rent; otherwise None."""
    if extract.low is None or not extract.evidence or extract.confidence <= 0:
        return None
    span, text = normalize_text(extract.evidence), normalize_text(snippet)
    if span not in text or _RENT.search(span) or not _SQFT.search(span):
        return None
    quoted = {float(n.replace(",", "")) for n in _NUMBER.findall(span)}
    high = extract.high if extract.high is not None else extract.low
    if not 0 < extract.low <= high or {extract.low, high} - quoted:
        return None
    return (extract.low + high) / 2


def _searched_level(
    ctx: PipelineContext, market: Market, locality: str, property_type: PropertyType
) -> Sourced[float] | None:
    query = f"{QUERY_WORDS[property_type]} price per sq ft in {locality} {market.query_city_name}"
    try:
        response = ctx.serp.search(*engines.google_search(query, ctx.settings), run_id=ctx.run_id)
        results = [
            {"index": i, "title": r.get("title"), "link": r.get("link"), "snippet": snippet}
            for i, r in enumerate(response.data.get("organic_results", [])[:MAX_RESULTS])
            if (snippet := r.get("snippet"))
        ]
        if not results:
            return None
        extract = ctx.llm.generate_structured(
            task="extract_price_level",
            prompt=prompt_for(
                "extract_price_level",
                locality=locality,
                property_type=QUERY_WORDS[property_type],
                results=results,
            ),
            schema=PriceLevelExtract,
            tier=ModelTier.LITE,
        )
    except AppError:
        return None  # a missing recording or a provider error falls back to the run's quotes
    chosen = next((r for r in results if r["index"] == extract.result_index), None)
    rate = supported_rate(extract, chosen["snippet"]) if chosen else None
    if rate is None:
        return None
    return Sourced(
        value=rate,
        confidence=min(extract.confidence, 0.7),
        method=ExtractionMethod.LLM,
        sources=[
            SourceRef(
                engine=SerpEngine.GOOGLE,
                url=chosen["link"],
                title=chosen["title"],
                search_id=response.search_id,
            )
        ],
        note=f'Evidence: "{extract.evidence}"',
    )
