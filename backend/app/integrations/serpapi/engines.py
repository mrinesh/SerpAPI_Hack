"""Parameter builders, one per SerpApi engine we use.

Every SerpApi request the platform makes is shaped here, so our usage can be audited in one file.
docs/SERPAPI_USAGE.md describes the same calls in prose. Each builder returns
`(engine, params)`, ready for `SerpApiGateway.search(*builder(...))`.

Status: parameter sets are drafted from the SerpApi docs and get confirmed against real
responses in spike S-01.
"""

from typing import Any

from app.config import Settings
from app.schemas.common import GeoPoint, SerpEngine

EngineCall = tuple[SerpEngine, dict[str, Any]]


def google_search(q: str, settings: Settings, *, num: int = 10, start: int = 0) -> EngineCall:
    """Listing discovery (site-filtered portal queries) and locality price-level lookups."""
    return SerpEngine.GOOGLE, {
        "q": q,
        "location": settings.serpapi_location,
        "google_domain": settings.serpapi_google_domain,
        "gl": settings.serpapi_gl,
        "hl": settings.serpapi_hl,
        "num": num,
        "start": start,
    }


def google_maps_search(
    q: str, settings: Settings, *, near: GeoPoint | None = None, zoom: int = 15
) -> EngineCall:
    """Geocoding a locality, nearby amenities, and same-category competitors."""
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
