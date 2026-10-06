"""F-05 locality aggregation. Partial payloads expire immediately so failures get retried.

Record mode rebuilds through the existing gateways so the derived cache cannot hide missing
raw recordings. Internal errors propagate; external failures become section-specific warnings.
"""

import logging
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field, ValidationError

from app.config import ProviderMode
from app.core.errors import AppError, UpstreamError
from app.db.models import AreaIntelRow
from app.integrations.llm.base import ModelTier
from app.integrations.serpapi import engines
from app.pipeline.context import PipelineContext
from app.pipeline.enrichment.area_sources import (
    locality_center,
    normalize_amenities,
    normalize_news,
    resolve_locality,
    search_source,
)
from app.pipeline.verification import prompt_for
from app.schemas.area import (
    AmenityCategory,
    AreaIntel,
    AreaIssue,
    InfrastructureFact,
    NewsTopic,
    Sentiment,
)
from app.schemas.profile import PropertyType
from app.schemas.provenance import ExtractionMethod, Sourced

log = logging.getLogger(__name__)
SCHEMA_VERSION = 3
AMENITY_QUERIES = {
    AmenityCategory.METRO: "metro station",
    AmenityCategory.SCHOOL: "school",
    AmenityCategory.HOSPITAL: "hospital",
}
INFRA_TOPICS = {NewsTopic.INFRASTRUCTURE, NewsTopic.CIVIC, NewsTopic.POLICY}


class NewsClassification(BaseModel):
    index: int = Field(ge=0)
    topic: NewsTopic
    sentiment: Sentiment


class ClassifiedNews(BaseModel):
    items: list[NewsClassification]


class EvidenceQuote(BaseModel):
    news_index: int = Field(ge=0)
    quote: str = Field(min_length=1)


class AreaSummaryEvidence(BaseModel):
    facts: list[EvidenceQuote] = Field(max_length=6)


def locality_key(locality: str, city: str) -> str:
    market, place = resolve_locality(locality, city)
    return f"{market.city.casefold()}/{place.slug}"


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def read_cached_area(row: AreaIntelRow) -> AreaIntel:
    try:
        area = AreaIntel.model_validate(row.data)
        if (
            area.locality_key != row.locality_key
            or as_utc(area.expires_at) != as_utc(row.expires_at)
            or as_utc(area.fetched_at) != as_utc(row.fetched_at)
        ):
            raise ValueError("cache metadata and payload disagree")
        return area
    except (ValidationError, ValueError) as exc:
        raise AppError(
            "Invalid area cache; rerun the profile to rebuild it.",
            details={
                "locality_key": row.locality_key,
                "operation": "area_cache_read",
            },
        ) from exc


def get_area_intel(
    ctx: PipelineContext,
    locality: str,
    *,
    benchmarks: dict[PropertyType, Sourced[float]] | None = None,
    now: datetime | None = None,
) -> AreaIntel:
    market, place = resolve_locality(locality, ctx.profile.city)
    key, now = locality_key(place.slug, market.city), now or datetime.now(UTC)
    modes = {"serpapi": str(ctx.settings.serpapi_mode), "llm": str(ctx.settings.llm_mode)}
    row = ctx.db.get(AreaIntelRow, key)
    recording = ProviderMode.RECORD in (ctx.settings.serpapi_mode, ctx.settings.llm_mode)
    if row is not None and as_utc(row.expires_at) > now and not recording:
        try:
            cached = read_cached_area(row)
        except AppError:
            log.warning("area cache invalid locality=%s; rebuilding", key)
        else:
            if cached.schema_version == SCHEMA_VERSION and cached.provider_modes == modes:
                log.debug("area cache hit locality=%s", key)
                return cached.model_copy(
                    update={"cache_hit": True, "price_levels": benchmarks or {}}
                )
    log.info("area cache miss locality=%s recording=%s", key, recording)
    area = AreaIntel(
        locality_key=key,
        locality=place.name,
        city=market.city,
        region=market.serpapi_location.split(",")[1],
        fetched_at=now,
        expires_at=now + timedelta(hours=ctx.settings.area_intel_ttl_hours),
        schema_version=SCHEMA_VERSION,
        provider_modes=modes,
    )

    def operation(name, provider, action):
        log.debug("area operation start locality=%s operation=%s provider=%s", key, name, provider)
        try:
            value = action()
        except AppError as exc:
            log.warning(
                "area operation failed locality=%s operation=%s provider=%s code=%s",
                key,
                name,
                provider,
                exc.code,
            )
            area.warnings.append(
                AreaIssue(operation=name, provider=provider, code=exc.code, message=exc.message)
            )
            area.section_status[name] = "failed"
            return None
        area.section_status[name] = "ok" if value else "empty"
        return value

    def search(call):
        response = ctx.serp.search(*call, run_id=ctx.run_id)
        area.sources.append(search_source(response))
        metadata = response.data.get("search_metadata", {})
        if not isinstance(metadata, dict):
            raise UpstreamError("Malformed SerpApi search metadata")
        if response.search_id and isinstance(metadata.get("created_at"), str):
            area.source_retrieved_at[response.search_id] = metadata["created_at"]
        return response

    def geocode():
        response = search(engines.google_maps_search(f"{place.name}, {market.city}", ctx.settings))
        area.center, area.center_source = locality_center(response, place)
        return area.center

    operation("center", "serpapi", geocode)
    if area.center is None:
        area.warnings.append(
            AreaIssue(
                operation="center",
                provider="serpapi",
                code="center_unavailable",
                message="No unambiguous locality coordinates; distances are unavailable.",
            )
        )
        if area.section_status["center"] != "failed":
            area.section_status["center"] = "unavailable"
    for category, words in AMENITY_QUERIES.items():

        def amenities(category=category, words=words):
            response = search(
                engines.google_maps_search(
                    f"{words} near {place.name} {market.city}",
                    ctx.settings,
                    near=area.center,
                )
            )
            return normalize_amenities(response, category, area.center, place)

        area.amenities.extend(operation(f"amenities:{category}", "serpapi", amenities) or [])

    def news():
        response = search(engines.google_news(f'"{place.name}" {market.city}', ctx.settings))
        return normalize_news(response, place)

    area.news = operation("news", "serpapi", news) or []
    # Run IDs/timestamps omitted so prompt keys remain stable across repeat runs.
    news_input = [
        {"index": i, "title": n.title, "snippet": n.snippet} for i, n in enumerate(area.news)
    ]

    def classify():
        result = ctx.llm.generate_structured(
            task="classify_news",
            prompt=prompt_for(
                "classify_news",
                locality=place.name,
                news_items=news_input,
            ),
            schema=ClassifiedNews,
            tier=ModelTier.LITE,
        )
        if sorted(item.index for item in result.items) != list(range(len(area.news))):
            raise UpstreamError("News classification must cover each input index exactly once")
        for item in result.items:
            area.news[item.index].topic, area.news[item.index].sentiment = (
                item.topic,
                item.sentiment,
            )
        return result.items

    if area.news:
        operation("classify_news", "deepseek", classify)
    else:
        area.section_status["classify_news"] = "empty"

    def summarize():
        result = ctx.llm.generate_structured(
            task="summarize_area",
            prompt=prompt_for(
                "summarize_area",
                locality=place.name,
                news_items=[
                    dict(item, topic=area.news[i].topic) for i, item in enumerate(news_input)
                ],
            ),
            schema=AreaSummaryEvidence,
            tier=ModelTier.REASONING,
        )
        facts, seen = [], set()
        for fact in result.facts:
            if fact.news_index >= len(area.news):
                raise UpstreamError("Infrastructure evidence refers to an unknown news index")
            article = area.news[fact.news_index]
            if article.topic not in INFRA_TOPICS:
                raise UpstreamError("Infrastructure evidence refers to an unrelated news topic")
            if not fact.quote.strip() or fact.quote not in (article.title, article.snippet):
                raise UpstreamError(
                    "Infrastructure evidence must preserve a complete title or snippet"
                )
            if (article.url, fact.quote) in seen:
                continue
            seen.add((article.url, fact.quote))
            facts.append(
                InfrastructureFact(
                    topic=article.topic,
                    evidence=Sourced(
                        value=fact.quote,
                        confidence=0.8,
                        method=ExtractionMethod.LLM,
                        sources=[article.source],
                        note="News evidence; project status is not independently verified.",
                    ),
                )
            )
        return facts

    if any(n.topic in INFRA_TOPICS for n in area.news):
        area.infrastructure = operation("summarize_area", "deepseek", summarize) or []
    else:
        area.section_status["summarize_area"] = (
            "unavailable" if area.section_status["classify_news"] == "failed" else "empty"
        )
    if area.infrastructure:
        area.infrastructure_summary = Sourced(
            value="\n".join(f.evidence.value for f in area.infrastructure),
            confidence=0.8,
            method=ExtractionMethod.LLM,
            sources=[s for f in area.infrastructure for s in f.evidence.sources],
            note="Exact news quotes selected by DeepSeek; see individual infrastructure facts.",
        )
    area.sources.extend(a.source for a in area.amenities)
    area.sources.extend(n.source for n in area.news)
    area.sources = list({s.model_dump_json(): s for s in area.sources}.values())
    area.summary = (
        f"{len(area.amenities)} amenity matches and {len(area.news)} locality-matched news items."
    )
    if area.warnings:
        area.expires_at = now
    # Cache excludes run-specific price types. Snapshots receive existing benchmarks.
    ctx.db.merge(
        AreaIntelRow(
            locality_key=key,
            data=area.model_dump(mode="json"),
            fetched_at=area.fetched_at,
            expires_at=area.expires_at,
        )
    )
    ctx.db.commit()
    log.info(
        "area complete locality=%s amenities=%s news=%s warnings=%s",
        key,
        len(area.amenities),
        len(area.news),
        len(area.warnings),
    )
    return area.model_copy(update={"price_levels": benchmarks or {}})
