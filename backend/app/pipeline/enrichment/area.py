"""Stage 5a, enrich: area intelligence for one locality (CHECKLIST F-05, ADR 0006, ADR 0016).

Computed once per locality and cached in `area_intel` for `area_intel_ttl_hours`; every listing
in that locality reuses it. Five searches per new locality (recorded in F-05):
- google_maps "<locality>, Bengaluru"                    -> centre point (geocoding, I-12)
- google_maps "metro station" / "school" / "hospital"   -> amenities near the centre
- google "<locality> Bangalore property price trend year on year" -> past-12-month growth
Distances are computed in code. DeepSeek lite reads the growth figure from one quoted snippet
(validated in code) and writes the summaries, which may quote only the figures they are given.
A provider error never fails a run, but it is never silent either (ADR 0019): the section is
marked failed with the error in `warnings`, and the area expires at once so the next run
retries. A cached area is reused only if it parses and matches the current schema version and
provider modes.
News and Google Trends demand are not collected yet.
"""

import logging
import math
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from pydantic import BaseModel, Field, ValidationError

from app.config import Settings
from app.core.errors import AppError
from app.db.models import AreaIntelRow
from app.integrations.llm.base import ModelTier
from app.integrations.serpapi import engines
from app.integrations.serpapi.engines import EngineCall
from app.pipeline.cleaning import normalize_text
from app.pipeline.context import PipelineContext
from app.pipeline.enrichment.rent_level import rent_level
from app.pipeline.grounding import allowed_numbers, grounded
from app.pipeline.verification import prompt_for
from app.reference import Market
from app.schemas.area import Amenity, AmenityCategory, AreaAccess, AreaIntel, AreaIssue
from app.schemas.common import GeoPoint, SerpEngine
from app.schemas.profile import PropertyType
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef

log = logging.getLogger(__name__)
T = TypeVar("T")
AREA_SCHEMA_VERSION = 2  # bump when AreaIntel's meaning changes, so cached areas are rebuilt

AMENITY_QUERIES: dict[AmenityCategory, str] = {
    AmenityCategory.METRO: "metro station",
    AmenityCategory.SCHOOL: "school",
    AmenityCategory.HOSPITAL: "hospital",
}
AMENITY_ZOOM = 14  # about a 5 km view around the centre
AMENITY_MAX_KM = 5.0
AMENITIES_PER_CATEGORY = 5
NEARBY_KM = 3.0  # "schools / hospitals within 3 km" (ADR 0016)
# Google Maps place types as recorded in F-05: "Subway station", "High school", "General hospital".
_TYPES: dict[AmenityCategory, re.Pattern[str]] = {
    AmenityCategory.METRO: re.compile(r"subway|metro|transit", re.I),
    AmenityCategory.SCHOOL: re.compile(r"school|educational institution", re.I),
    AmenityCategory.HOSPITAL: re.compile(r"hospital", re.I),
}
_NOT_A_SCHOOL = re.compile(
    r"pre-?school|play ?school|kindergarten|language|driving|coaching|tuition|music|dance|swim",
    re.I,
)
_RENT = re.compile(r"rent|lease|yield", re.I)
_PERIOD = re.compile(
    r"(?:last|past|in|over)\s+(?:one|1|12)\s*(?:year|yr|months?)|year[- ]on[- ]year|yoy|y-o-y"
    r"|annual",
    re.I,
)
_FALL = re.compile(r"fall|fell|drop|decline|decrease|down|dip|-\s*\d", re.I)
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
MAX_GROWTH_RESULTS = 8


class PriceGrowthExtract(BaseModel):
    """Output schema of the `extract_price_growth` prompt."""

    result_index: int | None
    pct: float | None
    evidence: str | None
    confidence: float = Field(ge=0, le=1)


class LongRunGrowthExtract(BaseModel):
    """Output schema of the `extract_long_run_growth` prompt."""

    result_index: int | None
    total_pct: float | None
    years: int | None
    evidence: str | None
    confidence: float = Field(ge=0, le=1)


class AreaSummary(BaseModel):
    """Output schema of the `summarize_area` prompt."""

    summary: str
    infrastructure_summary: str


# --- query builders -----------------------------------------------------------------------


def locality_key(locality: str, city: str) -> str:
    """Normalised slug used as the cache key.

    ("Whitefield ", "Bengaluru") -> "bengaluru/whitefield"
    """
    return "/".join(
        re.sub(r"[^a-z0-9]+", "-", part.strip().lower()).strip("-") for part in (city, locality)
    )


def geocode_call(name: str, market: Market, settings: Settings) -> EngineCall:
    return engines.google_maps_search(f"{name}, {market.city}", settings)


def amenity_call(category: AmenityCategory, centre: GeoPoint, settings: Settings) -> EngineCall:
    return engines.google_maps_search(
        AMENITY_QUERIES[category], settings, near=centre, zoom=AMENITY_ZOOM
    )


def growth_call(name: str, market: Market, settings: Settings) -> EngineCall:
    return engines.google_search(
        f"{name} {market.query_city_name} property price trend year on year", settings
    )


# --- pure parsing and distances -----------------------------------------------------------


def haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (a.lat, a.lng, b.lat, b.lng))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _gps(item: dict) -> GeoPoint | None:
    gps = item.get("gps_coordinates") or {}
    if "latitude" not in gps or "longitude" not in gps:
        return None
    return GeoPoint(lat=gps["latitude"], lng=gps["longitude"])


def parse_centre(data: dict, market: Market) -> GeoPoint | None:
    """The place result's point, else the first local result's; None outside the city box."""
    point = _gps(data.get("place_results") or {})
    if point is None:
        point = next((p for p in map(_gps, data.get("local_results") or []) if p), None)
    if point is None or (market.bounds and not market.bounds.contains(point.lat, point.lng)):
        return None
    return point


def parse_amenities(
    data: dict, category: AmenityCategory, centre: GeoPoint, search_id: str | None
) -> list[Amenity]:
    found: dict[str, Amenity] = {}
    for place in data.get("local_results") or []:
        kind, name, point = place.get("type") or "", (place.get("title") or "").strip(), _gps(place)
        if not name or point is None or not _TYPES[category].search(kind):
            continue
        if category is AmenityCategory.SCHOOL and _NOT_A_SCHOOL.search(f"{kind} {name}"):
            continue
        distance = round(haversine_km(centre, point), 2)
        if distance > AMENITY_MAX_KM or name.lower() in found:
            continue
        found[name.lower()] = Amenity(
            name=name,
            category=category,
            location=point,
            distance_km=distance,
            rating=place.get("rating"),
            reviews=place.get("reviews"),
            source=SourceRef(
                engine=SerpEngine.GOOGLE_MAPS,
                url=place.get("place_id_search") or place.get("link"),
                title=name,
                search_id=search_id,
            ),
        )
    return sorted(found.values(), key=lambda a: a.distance_km or 0)[:AMENITIES_PER_CATEGORY]


def supported_growth(extract: PriceGrowthExtract, snippet: str) -> float | None:
    """The signed percentage when the span is in the snippet, states it with "%" and a
    12-month period, is not about rent, and its direction agrees with the sign."""
    if extract.pct is None or not extract.evidence or extract.confidence <= 0:
        return None
    span, text = normalize_text(extract.evidence), normalize_text(snippet)
    if span not in text or _RENT.search(span) or not _PERIOD.search(span):
        return None
    quoted = {
        float(m.group().replace(",", ""))
        for m in _NUMBER.finditer(span)
        if span[m.end() : m.end() + 2].lstrip().startswith("%")
    }
    if abs(extract.pct) not in quoted or extract.pct == 0:
        return None
    if (extract.pct < 0) != bool(_FALL.search(span)):
        return None
    return extract.pct


_YEAR_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
               "nine": 9, "ten": 10}  # fmt: skip
_YEARS = re.compile(r"\b(\d+|" + "|".join(_YEAR_WORDS) + r")\s*(?:-\s*)?(?:years?|yrs?)\b", re.I)
MIN_YEARS, MAX_YEARS = 2, 10


def annualised(total_pct: float, years: int) -> float:
    """Compound yearly rate from a total change over `years`: (1 + total)^(1/years) - 1."""
    return ((1 + total_pct / 100) ** (1 / years) - 1) * 100


def supported_long_run(extract: LongRunGrowthExtract, snippet: str) -> float | None:
    """The yearly rate when the span is in the snippet and quotes the total "%" change and its
    multi-year period (2-10 years), is not about rent, and its direction matches the sign."""
    if extract.total_pct is None or extract.years is None or not extract.evidence:
        return None
    if extract.confidence <= 0 or not MIN_YEARS <= extract.years <= MAX_YEARS:
        return None
    span, text = normalize_text(extract.evidence), normalize_text(snippet)
    if span not in text or _RENT.search(span):
        return None
    periods = {
        int(m.group(1)) if m.group(1).isdigit() else _YEAR_WORDS[m.group(1).lower()]
        for m in _YEARS.finditer(span)
    }
    quoted = {
        float(m.group().replace(",", ""))
        for m in _NUMBER.finditer(span)
        if span[m.end() : m.end() + 2].lstrip().startswith("%")
    }
    if extract.years not in periods or abs(extract.total_pct) not in quoted:
        return None
    if extract.total_pct == 0 or (extract.total_pct < 0) != bool(_FALL.search(span)):
        return None
    return round(annualised(extract.total_pct, extract.years), 2)


def access_from(point: GeoPoint, area: AreaIntel, measured_from: str) -> AreaAccess:
    def distances(category: AmenityCategory) -> list[tuple[float, str]]:
        return sorted(
            (haversine_km(point, a.location), a.name)
            for a in area.amenities
            if a.category is category and a.location is not None
        )

    metros = distances(AmenityCategory.METRO)
    return AreaAccess(
        metro_name=metros[0][1] if metros else None,
        metro_km=round(metros[0][0], 1) if metros else None,
        schools_3km=sum(d <= NEARBY_KM for d, _ in distances(AmenityCategory.SCHOOL)),
        hospitals_3km=sum(d <= NEARBY_KM for d, _ in distances(AmenityCategory.HOSPITAL)),
        measured_from=measured_from,
    )


def listing_access(location: GeoPoint | None, area: AreaIntel | None) -> AreaAccess | None:
    """Measured from the listing's own point when it has one (Maps projects), else the centre."""
    if area is None or not area.amenities:
        return None
    if location is not None:
        return access_from(location, area, "listing")
    if area.center is None:
        return None
    return access_from(area.center, area, "locality centre")


# --- summaries ----------------------------------------------------------------------------


def growth_text(growth: Sourced[float] | None) -> str | None:
    if growth is None or growth.value is None:
        return None
    return f"{growth.value:g}% over the past 12 months"


def summary_figures(
    name: str,
    amenities: list[Amenity],
    growth: Sourced[float] | None,
    centre_access: AreaAccess | None,
) -> dict[str, str]:
    figures = {"locality": name}
    if centre_access is not None:
        figures["schools"] = f"{centre_access.schools_3km} schools found within 3 km"
        figures["hospitals"] = f"{centre_access.hospitals_3km} hospitals found within 3 km"
    # Keyed by category ("metro_station_1"): without it the model took a metro station named
    # "Sri Sathya Sai Hospital" for a hospital (recorded in F-05).
    counts: dict[AmenityCategory, int] = {}
    for amenity in amenities:
        counts[amenity.category] = counts.get(amenity.category, 0) + 1
        label = AMENITY_QUERIES[amenity.category].replace(" ", "_")
        figures[f"{label}_{counts[amenity.category]}"] = (
            f"{amenity.name}, {amenity.distance_km:.1f} km"
        )
    if text := growth_text(growth):
        figures["price_growth"] = text
    return figures


def code_summary(
    name: str,
    amenities: list[Amenity],
    growth: Sourced[float] | None,
    centre_access: AreaAccess | None,
) -> tuple[str, str]:
    metro = next((a for a in amenities if a.category is AmenityCategory.METRO), None)
    infra = (
        f"Nearest metro station: {metro.name}, {metro.distance_km:.1f} km from the centre "
        f"of {name}."
        if metro
        else f"No metro station found within {AMENITY_MAX_KM:g} km of the centre of {name}."
    )
    parts = []
    if centre_access is not None:
        parts.append(
            f"{centre_access.schools_3km} schools and {centre_access.hospitals_3km} hospitals "
            f"found within 3 km of the centre."
        )
    if text := growth_text(growth):
        parts.append(f"Quoted price change: {text}.")
    return " ".join(parts) or f"Little area data was found for {name}.", infra


class Sections:
    """Runs each part of an area, recording "ok", "empty" or "failed" with the error, so a
    provider failure is visible instead of looking like missing data (ADR 0019)."""

    def __init__(self, area: AreaIntel) -> None:
        self.area = area

    def run(self, name: str, provider: str, action: Callable[[], T]) -> T | None:
        self.area.warnings = [w for w in self.area.warnings if w.section != name]
        try:
            value = action()
        except AppError as exc:
            log.warning(
                "area section failed locality=%s section=%s provider=%s code=%s",
                self.area.locality_key,
                name,
                provider,
                exc.code,
            )
            self.area.warnings.append(
                AreaIssue(section=name, provider=provider, code=exc.code, message=exc.message)
            )
            self.area.section_status[name] = "failed"
            return None
        self.area.section_status[name] = "ok" if value else "empty"
        return value

    @property
    def failed(self) -> bool:
        return "failed" in self.area.section_status.values()


def _summarize(
    ctx: PipelineContext,
    name: str,
    amenities: list[Amenity],
    growth: Sourced[float] | None,
    centre_access: AreaAccess | None,
    sections: Sections | None = None,
) -> tuple[str, str, bool]:
    fallback = code_summary(name, amenities, growth, centre_access)
    if not amenities and growth is None:
        return (*fallback, False)
    figures = summary_figures(name, amenities, growth, centre_access)

    def write() -> AreaSummary:
        return ctx.llm.generate_structured(
            task="summarize_area",
            prompt=prompt_for("summarize_area", figures=figures),
            schema=AreaSummary,
            tier=ModelTier.LITE,
        )

    if sections is not None:
        written = sections.run("summary", "deepseek", write)
    else:
        try:
            written = write()
        except AppError:
            written = None
    if written is None:
        return (*fallback, False)
    allowed = allowed_numbers(figures)
    if all(
        text.strip() and grounded(text, allowed)
        for text in (written.summary, written.infrastructure_summary)
    ):
        return written.summary.strip(), written.infrastructure_summary.strip(), True
    return (*fallback, False)


# --- searches -----------------------------------------------------------------------------


def _search(ctx: PipelineContext, call: EngineCall):
    """Raises AppError on any provider failure; callers record it as a failed section."""
    return ctx.serp.search(*call, run_id=ctx.run_id)


def _growth(ctx: PipelineContext, name: str, market: Market) -> Sourced[float] | None:
    response = _search(ctx, growth_call(name, market, ctx.settings))
    results = [
        {"index": i, "title": r.get("title"), "link": r.get("link"), "snippet": snippet}
        for i, r in enumerate(response.data.get("organic_results", [])[:MAX_GROWTH_RESULTS])
        if (snippet := r.get("snippet"))
    ]
    if not results:
        return None
    extract = ctx.llm.generate_structured(
        task="extract_price_growth",
        prompt=prompt_for("extract_price_growth", locality=name, results=results),
        schema=PriceGrowthExtract,
        tier=ModelTier.LITE,
    )
    chosen = next((r for r in results if r["index"] == extract.result_index), None)
    pct = supported_growth(extract, chosen["snippet"]) if chosen else None
    if pct is None:
        return None
    return Sourced(
        value=pct,
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
        note=f'Past 12 months, not a forecast. Evidence: "{extract.evidence}"',
    )


def provider_modes(settings: Settings) -> dict[str, str]:
    return {"serpapi": str(settings.serpapi_mode), "llm": str(settings.llm_mode)}


def build_area_intel(ctx: PipelineContext, market: Market, slug: str) -> AreaIntel:
    place = market.locality(slug)
    name = place.name if place else slug.replace("-", " ").title()
    now = datetime.now(UTC)
    area = AreaIntel(
        locality_key=locality_key(name, market.city),
        locality=name,
        city=market.city,
        schema_version=AREA_SCHEMA_VERSION,
        provider_modes=provider_modes(ctx.settings),
        fetched_at=now,
        expires_at=now + timedelta(hours=ctx.settings.area_intel_ttl_hours),
    )
    sections = Sections(area)
    area.center = sections.run(
        "centre",
        "serpapi",
        lambda: parse_centre(_search(ctx, geocode_call(name, market, ctx.settings)).data, market),
    )
    if area.center is not None:
        for category in AMENITY_QUERIES:

            def nearby(category: AmenityCategory = category) -> list[Amenity]:
                response = _search(ctx, amenity_call(category, area.center, ctx.settings))
                return parse_amenities(response.data, category, area.center, response.search_id)

            area.amenities += sections.run(str(category), "serpapi", nearby) or []
    area.price_growth_pct = sections.run(
        "growth", "serpapi+deepseek", lambda: _growth(ctx, name, market)
    )
    centre_access = (
        access_from(area.center, area, "locality centre")
        if area.center and area.amenities
        else None
    )
    area.summary, area.infrastructure_summary, area.summary_by_ai = _summarize(
        ctx, name, area.amenities, area.price_growth_pct, centre_access, sections
    )
    if sections.failed:
        area.expires_at = area.fetched_at  # keep it to inspect, but retry on the next run
    return area


def read_cached(row: AreaIntelRow | None, settings: Settings) -> AreaIntel | None:
    """The cached area when it is still valid for the running code and providers, else None."""
    if row is None:
        return None
    expires = row.expires_at.replace(tzinfo=row.expires_at.tzinfo or UTC)
    if expires <= datetime.now(UTC):
        return None
    try:
        area = AreaIntel.model_validate(row.data)
    except ValidationError:
        log.warning("area cache unreadable locality=%s; rebuilding", row.locality_key)
        return None
    if area.schema_version != AREA_SCHEMA_VERSION or area.provider_modes != provider_modes(
        settings
    ):
        log.info(
            "area cache from other code or providers locality=%s; rebuilding", row.locality_key
        )
        return None
    return area


def get_area_intel(
    ctx: PipelineContext,
    market: Market,
    slug: str,
    levels: dict[PropertyType, Sourced[float]] | None = None,
    types: set[PropertyType] | None = None,
) -> tuple[AreaIntel, bool]:
    """The cached area for `slug` (built when missing or expired), with this run's price levels
    merged in and a rent level fetched for each of `types` it lacks (F-09). Returns
    (area, served_from_cache)."""
    place = market.locality(slug)
    key = locality_key(place.name if place else slug, market.city)
    row = ctx.db.get(AreaIntelRow, key)
    area = read_cached(row, ctx.settings)
    cached = area is not None
    log.info("area cache %s locality=%s", "hit" if cached else "miss", key)
    if area is None:
        area = build_area_intel(ctx, market, slug)
    merged = {**area.price_levels, **(levels or {})}
    area.price_levels = {PropertyType(kind): level for kind, level in merged.items()}
    sections = Sections(area)
    for kind in sorted(types or set()):
        if PropertyType(kind) not in area.rent_levels:
            # Missing rent is fetched on every run (cheap once cached), so its failure does not
            # need to expire the rest of the area.
            found = sections.run(
                f"rent:{kind}",
                "serpapi+deepseek",
                lambda kind=kind: rent_level(ctx, market, area.locality, PropertyType(kind)),
            )
            if found is not None:
                area.rent_levels[PropertyType(kind)] = found
    if row is None:
        row = AreaIntelRow(locality_key=key)
        ctx.db.add(row)
    row.data = area.model_dump(mode="json")
    row.fetched_at, row.expires_at = area.fetched_at, area.expires_at
    ctx.db.commit()
    return area, cached


def long_run_growth(ctx: PipelineContext, name: str, market: Market) -> Sourced[float] | None:
    """Average yearly price change over several years, from the growth search's results (used
    for suggested targets, ADR 0018). Reuses the F-05 search, so it adds one lite call."""
    try:
        response = _search(ctx, growth_call(name, market, ctx.settings))
    except AppError:
        return None  # a suggestion never fails; the target field simply stays empty
    results = [
        {"index": i, "title": r.get("title"), "link": r.get("link"), "snippet": snippet}
        for i, r in enumerate(response.data.get("organic_results", [])[:MAX_GROWTH_RESULTS])
        if (snippet := r.get("snippet"))
    ]
    if not results:
        return None
    try:
        extract = ctx.llm.generate_structured(
            task="extract_long_run_growth",
            prompt=prompt_for("extract_long_run_growth", locality=name, results=results),
            schema=LongRunGrowthExtract,
            tier=ModelTier.LITE,
        )
    except AppError:
        return None
    chosen = next((r for r in results if r["index"] == extract.result_index), None)
    rate = supported_long_run(extract, chosen["snippet"]) if chosen else None
    if rate is None:
        return None
    return Sourced(
        value=rate,
        confidence=min(extract.confidence, 0.6),
        method=ExtractionMethod.COMPUTED,
        sources=[
            SourceRef(
                engine=SerpEngine.GOOGLE,
                url=chosen["link"],
                title=chosen["title"],
                search_id=response.search_id,
            )
        ],
        note=(
            f"Average a year over {extract.years} years; past data, not a forecast. "
            f'Evidence: "{extract.evidence}"'
        ),
    )
