"""Stage 5b, enrich: same-category businesses around a commercial locality (CHECKLIST F-06,
ADR 0023).

Only for commercial profiles with a `business_type`. Commercial candidates carry no GPS (S-01),
so the report is per locality and business type, centred on the area's geocoded centre (F-05):
- google_maps "<business_type>" at the centre, zoom 15 -> one page of up to 20 places.
Distances, the count within `RADIUS_KM`, density, average rating and review volume are computed
in code; no LLM is involved. What the count means depends on the property type: competition for
a shop, a business cluster for an office, warehouse or land (`READINGS`).
Cached in `competitor_reports` for `area_intel_ttl_hours`. A failed search never fails the run:
the report says so and expires at once, so the next run retries (as areas do, ADR 0019).
F-06b: a bounded first page of reviews -> cited, evidence-checked complaint themes.
"""

import hashlib
import logging
import math
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from app.config import Settings
from app.core.errors import AppError
from app.db.models import CompetitorReportRow
from app.integrations.serpapi import engines
from app.integrations.serpapi.engines import EngineCall
from app.pipeline.context import PipelineContext
from app.pipeline.enrichment.area import haversine_km, place_point, provider_modes
from app.pipeline.enrichment.competitor_reviews import enrich_reviews
from app.schemas.area import AreaIntel, AreaIssue
from app.schemas.common import GeoPoint, Level, SerpEngine
from app.schemas.competitor import Competitor, CompetitorReading, CompetitorReport
from app.schemas.profile import PropertyType
from app.schemas.provenance import SourceRef

log = logging.getLogger(__name__)
COMPETITOR_SCHEMA_VERSION = 2  # F-06b adds review evidence and checked complaint themes
COMPETITOR_ZOOM = 15  # about a 2-3 km view; Maps still returns places farther out
RADIUS_KM = 2.0  # roughly a locality; places beyond it are dropped
HIGH_COUNT, MEDIUM_COUNT = 10, 4  # places within the radius, out of one page of 20 (ADR 0023)

READINGS: dict[PropertyType, CompetitorReading] = {
    PropertyType.SHOP_SHOWROOM: CompetitorReading.COMPETITION,
    PropertyType.OFFICE: CompetitorReading.CLUSTER,
    PropertyType.WAREHOUSE: CompetitorReading.CLUSTER,
    PropertyType.COMMERCIAL_LAND: CompetitorReading.CLUSTER,
}


def competitor_call(business_type: str, centre: GeoPoint, settings: Settings) -> EngineCall:
    return engines.google_maps_search(business_type, settings, near=centre, zoom=COMPETITOR_ZOOM)


# --- pure parsing and figures -------------------------------------------------------------


def parse_competitors(
    data: dict, centre: GeoPoint, search_id: str | None, radius_km: float = RADIUS_KM
) -> list[Competitor]:
    """Places with a position within `radius_km` of the centre, once each, nearest first."""
    found: dict[str, Competitor] = {}
    for place in data.get("local_results") or []:
        name, point = (place.get("title") or "").strip(), place_point(place)
        if not name or point is None:
            continue
        distance = round(haversine_km(centre, point), 2)
        key = place.get("place_id") or name.lower()
        if distance > radius_km or key in found:
            continue
        found[key] = Competitor(
            name=name,
            category=place.get("type") or "",
            location=point,
            distance_km=distance,
            rating=place.get("rating"),
            reviews=place.get("reviews"),
            place_id=place.get("place_id"),
            data_id=place.get("data_id"),
            source=SourceRef(
                engine=SerpEngine.GOOGLE_MAPS,
                url=place.get("place_id_search") or place.get("link"),
                title=name,
                search_id=search_id,
            ),
        )
    return sorted(found.values(), key=lambda c: c.distance_km or 0)


def density_level(count: int) -> Level:
    """10+ places within the radius is high, 4-9 medium, fewer low (out of a page of 20)."""
    return (
        Level.HIGH if count >= HIGH_COUNT else Level.MEDIUM if count >= MEDIUM_COUNT else Level.LOW
    )


def fill_figures(report: CompetitorReport) -> None:
    """Density, level, average rating and total reviews from `report.competitors`."""
    places = report.competitors
    rated = [c.rating for c in places if c.rating is not None]
    report.density_per_sq_km = round(len(places) / (math.pi * report.radius_km**2), 2)
    report.density_level = density_level(len(places))
    report.avg_rating = round(sum(rated) / len(rated), 1) if rated else None
    report.total_reviews = sum(c.reviews or 0 for c in places)


def readings_for(types: set[PropertyType]) -> dict[PropertyType, CompetitorReading]:
    return {kind: READINGS[kind] for kind in sorted(types) if kind in READINGS}


def report_key(area: AreaIntel, business_type: str, radius_km: float = RADIUS_KM) -> str:
    """Hash of (locality, rounded centre, business type, radius); a re-geocoded centre or a
    different business misses the cache."""
    centre = area.center
    parts = [
        area.locality_key,
        f"{centre.lat:.4f},{centre.lng:.4f}" if centre else "",
        " ".join(business_type.lower().split()),
        f"{radius_km:g}",
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


# --- build and cache ----------------------------------------------------------------------


def build_report(ctx: PipelineContext, area: AreaIntel, business_type: str) -> CompetitorReport:
    """One search at the area's centre; a provider error becomes a visible "failed" report."""
    now = datetime.now(UTC)
    report = CompetitorReport(
        locality_key=area.locality_key,
        locality=area.locality,
        business_type=business_type,
        center=area.center,
        radius_km=RADIUS_KM,
        schema_version=COMPETITOR_SCHEMA_VERSION,
        provider_modes=provider_modes(ctx.settings),
        fetched_at=now,
        expires_at=now + timedelta(hours=ctx.settings.area_intel_ttl_hours),
    )
    try:
        response = ctx.serp.search(
            *competitor_call(business_type, area.center, ctx.settings), run_id=ctx.run_id
        )
    except AppError as exc:
        log.warning(
            "competitor search failed locality=%s business=%s code=%s",
            area.locality_key,
            business_type,
            exc.code,
        )
        report.status = "failed"
        report.warning = AreaIssue(
            section="competitors", provider="serpapi", code=exc.code, message=exc.message
        )
        report.expires_at = report.fetched_at
        return report
    report.results_seen = len(response.data.get("local_results") or [])
    report.more_available = bool((response.data.get("serpapi_pagination") or {}).get("next"))
    report.competitors = parse_competitors(response.data, area.center, response.search_id)
    report.status = "ok" if report.competitors else "empty"
    fill_figures(report)
    enrich_reviews(ctx, report)
    if report.review_warnings:
        report.expires_at = report.fetched_at
    return report


def read_cached(row: CompetitorReportRow | None, settings: Settings) -> CompetitorReport | None:
    """The cached report when unexpired and from the running code and providers, else None."""
    if row is None:
        return None
    expires = row.expires_at.replace(tzinfo=row.expires_at.tzinfo or UTC)
    if expires <= datetime.now(UTC):
        return None
    try:
        report = CompetitorReport.model_validate(row.data)
    except ValidationError:
        log.warning("competitor cache unreadable key=%s; rebuilding", row.key)
        return None
    if report.schema_version != COMPETITOR_SCHEMA_VERSION or report.provider_modes != (
        provider_modes(settings)
    ):
        return None
    if report.review_places_limit != settings.competitor_review_max_places:
        return None
    return report


def get_competitor_report(
    ctx: PipelineContext, area: AreaIntel, business_type: str, types: set[PropertyType]
) -> tuple[CompetitorReport, bool] | None:
    """The report around the area's centre for `business_type`, built when missing or expired,
    with readings for the profile's `types`. None when the area has no centre (nothing to search
    around). Returns (report, served_from_cache)."""
    if area.center is None:
        return None
    key = report_key(area, business_type)
    row = ctx.db.get(CompetitorReportRow, key)
    report = read_cached(row, ctx.settings)
    cached = report is not None
    log.info("competitor cache %s locality=%s", "hit" if cached else "miss", area.locality_key)
    if report is None:
        report = build_report(ctx, area, business_type)
        if row is None:
            row = CompetitorReportRow(key=key)
            ctx.db.add(row)
        row.data = report.model_dump(mode="json")
        row.fetched_at, row.expires_at = report.fetched_at, report.expires_at
        ctx.db.commit()
    report.readings = readings_for(types)  # per profile, so never taken from the cache
    return report, cached
