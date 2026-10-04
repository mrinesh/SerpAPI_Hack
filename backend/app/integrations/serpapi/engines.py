"""Parameter builders, one per SerpApi engine we use.

Every SerpApi request the platform makes is shaped here, so our usage can be audited in one file.
docs/SERPAPI_USAGE.md describes the same calls in prose. Each builder returns
`(engine, params)`, ready for `SerpApiGateway.search(*builder(...))`.

Parameters follow SerpApi's docs (checked 2026-10-04); spike S-01 confirms them against real
responses.
"""

from typing import Any

from app.config import Settings
from app.schemas.common import GeoPoint, SerpEngine

EngineCall = tuple[SerpEngine, dict[str, Any]]


def google_search(q: str, settings: Settings, *, start: int = 0) -> EngineCall:
    """Listing discovery (site-filtered portal queries) and locality price-level lookups.

    Paginate with `start` (0, 10, 20...). SerpApi's Google Search docs list no `num` parameter.
    """
    return SerpEngine.GOOGLE, {
        "q": q,
        "location": settings.serpapi_location,
        "google_domain": settings.serpapi_google_domain,
        "gl": settings.serpapi_gl,
        "hl": settings.serpapi_hl,
        "start": start,
    }


def google_local(q: str, settings: Settings, *, start: int = 0) -> EngineCall:
    """Google's local results (businesses with address, type, GPS) for a query and location."""
    return SerpEngine.GOOGLE_LOCAL, {
        "q": q,
        "location": settings.serpapi_location,
        "google_domain": settings.serpapi_google_domain,
        "gl": settings.serpapi_gl,
        "hl": settings.serpapi_hl,
        "start": start,
    }


def google_maps_search(
    q: str, settings: Settings, *, near: GeoPoint | None = None, zoom: int = 15
) -> EngineCall:
    """Geocoding a locality, nearby amenities, and same-category competitors.

    Results come in pages of 20 (`start` 0, 20, 40...). `ll` is optional with `q`.
    """
    params: dict[str, Any] = {"q": q, "type": "search", "hl": settings.serpapi_hl}
    if near is not None:
        params["ll"] = f"@{near.lat},{near.lng},{zoom}z"
    return SerpEngine.GOOGLE_MAPS, params


def google_maps_reviews(
    data_id: str, settings: Settings, *, sort_by: str = "qualityScore"
) -> EngineCall:
    """Competitor review text, used to find gaps in the local market."""
    return SerpEngine.GOOGLE_MAPS_REVIEWS, {
        "data_id": data_id,
        "hl": settings.serpapi_hl,
        "sort_by": sort_by,
    }


def google_news(q: str, settings: Settings) -> EngineCall:
    """Neighbourhood news and infrastructure announcements."""
    return SerpEngine.GOOGLE_NEWS, {"q": q, "gl": settings.serpapi_gl, "hl": settings.serpapi_hl}


def google_trends(
    queries: list[str], *, geo: str = "IN-KA", date: str = "today 12-m"
) -> EngineCall:
    """Search interest over time; a demand proxy for buying and renting in a locality.

    Google Trends compares at most 5 queries per request.
    """
    return SerpEngine.GOOGLE_TRENDS, {
        "q": ",".join(queries[:5]),
        "geo": geo,
        "date": date,
        "data_type": "TIMESERIES",
    }
