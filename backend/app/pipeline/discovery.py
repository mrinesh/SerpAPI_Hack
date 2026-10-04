"""Stage 2, fetch: run planned queries through the SerpApi gateway (CHECKLIST F-02).

Google results are kept only when they come from the three portals and are not for-rent pages;
Google Maps places only when their type is a housing type seen in S-01. A Google query with no
portal results is retried once without the budget phrase. A run that hits its search budget
stops searching and keeps what it has.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.errors import AppError, SearchBudgetExceeded
from app.integrations.serpapi.gateway import SerpResponse
from app.pipeline.cleaning import HOUSING_PLACE_TYPES, detect_portal, is_rental_page
from app.pipeline.context import PipelineContext
from app.pipeline.query_planner import PlannedQuery
from app.schemas.common import GeoPoint, SerpEngine
from app.schemas.listing import RawSearchHit


@dataclass
class FetchReport:
    searches: int = 0  # gateway calls that returned a response
    live: int = 0  # of which spent a search credit
    retries: int = 0
    empty: list[str] = field(default_factory=list)  # purposes that found nothing usable
    errors: list[str] = field(default_factory=list)
    stopped_early: bool = False


def fetch_hits(
    ctx: PipelineContext, queries: list[PlannedQuery]
) -> tuple[list[RawSearchHit], FetchReport]:
    report = FetchReport()
    hits: list[RawSearchHit] = []
    for query in queries:
        try:
            found = _run(ctx, query, query.params, report)
            if not found and query.retry_params is not None:
                report.retries += 1
                found = _run(ctx, query, query.retry_params, report)
        except SearchBudgetExceeded as exc:
            report.errors.append(exc.message)
            report.stopped_early = True
            break
        except AppError as exc:
            report.errors.append(f"{query.purpose}: {exc.message}")
            continue
        if not found:
            report.empty.append(query.purpose)
        hits.extend(found)
    return hits, report


def _run(
    ctx: PipelineContext, query: PlannedQuery, params: dict[str, Any], report: FetchReport
) -> list[RawSearchHit]:
    response = ctx.serp.search(query.engine, params, run_id=ctx.run_id)
    report.searches += 1
    report.live += int(response.live)
    if query.engine is SerpEngine.GOOGLE_MAPS:
        return _places(response, query)
    return _portal_pages(response, query)


def _portal_pages(response: SerpResponse, query: PlannedQuery) -> list[RawSearchHit]:
    hits = []
    for result in response.data.get("organic_results", []):
        link, title = result.get("link") or "", result.get("title") or ""
        if detect_portal(link) is None or is_rental_page(title, link):
            continue
        hits.append(
            RawSearchHit(
                engine=SerpEngine.GOOGLE,
                query=response.params["q"],
                locality=query.locality,
                property_type=query.property_type,
                position=result.get("position"),
                title=title,
                link=link,
                snippet=result.get("snippet"),
                search_id=response.search_id,
                fetched_at=datetime.now(UTC),
            )
        )
    return hits


def _places(response: SerpResponse, query: PlannedQuery) -> list[RawSearchHit]:
    hits = []
    for place in response.data.get("local_results", []):
        if place.get("type") not in HOUSING_PLACE_TYPES:
            continue
        gps = place.get("gps_coordinates") or {}
        hits.append(
            RawSearchHit(
                engine=SerpEngine.GOOGLE_MAPS,
                query=response.params["q"],
                locality=query.locality,
                property_type=query.property_type,
                position=place.get("position"),
                title=place.get("title") or "",
                gps=GeoPoint(lat=gps["latitude"], lng=gps["longitude"]) if gps else None,
                place_type=place.get("type"),
                address=place.get("address"),
                rating=place.get("rating"),
                reviews=place.get("reviews"),
                place_id=place.get("place_id"),
                search_id=response.search_id,
                fetched_at=datetime.now(UTC),
            )
        )
    return hits
