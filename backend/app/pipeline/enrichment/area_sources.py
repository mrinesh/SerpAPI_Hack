"""F-05 provider normalization. No network or database access lives in this module.

Maps distances are straight-line distances from the sourced locality centre. News requires
a whole locality name/alias in its own title or snippet; query membership is not evidence.
"""

import math
import re
import unicodedata
from datetime import datetime
from urllib.parse import quote, urlsplit, urlunsplit

from pydantic import BaseModel, Field, ValidationError

from app.core.errors import InvalidInput, UpstreamError
from app.integrations.serpapi.gateway import SerpResponse
from app.reference import Locality, Market, load_market
from app.schemas.area import Amenity, AmenityCategory, NewsItem
from app.schemas.common import GeoPoint
from app.schemas.provenance import SourceRef

MAX_NEWS = 12
MAX_AMENITIES = 5  # per category
AMENITY_RADIUS_KM = 10


def normalized_name(value: str) -> str:
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold()))


def resolve_locality(locality: str, city: str) -> tuple[Market, Locality]:
    market = load_market(city)
    if market is None:
        # City aliases are already declared by each supported market.
        market = load_market("Bengaluru")
        if normalized_name(city) not in {normalized_name(c) for c in market.city_aliases}:
            raise InvalidInput(["city"], "Unsupported city")
    name = normalized_name(locality)
    place = next(
        (
            p
            for p in market.localities
            if name in {normalized_name(v) for v in (p.slug, p.name, *p.aliases)}
        ),
        None,
    )
    if place is None:
        raise InvalidInput(["locality"], f"Unknown locality in {market.city}: {locality}")
    return market, place


def mentions_locality(text: str, place: Locality) -> bool:
    normalized = f" {normalized_name(text)} "
    return any(f" {normalized_name(name)} " in normalized for name in (place.name, *place.aliases))


def http_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    return value if parsed.scheme in {"https", "http"} and parsed.netloc else None


def search_source(response: SerpResponse) -> SourceRef:
    # Never expose the provider's request URL: it can contain an API key.
    q = quote(str(response.params.get("q", "")))
    host = "https://www.google.com/maps/search/?api=1&query="
    if response.engine == "google_news":
        host = "https://news.google.com/search?q="
    return SourceRef(
        engine=response.engine,
        url=host + q,
        title=str(response.params.get("q", "")),
        search_id=response.search_id,
    )


def _objects(data: dict, key: str) -> list[dict]:
    rows = data.get(key, [])
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise UpstreamError(f"Malformed SerpApi {key}: expected a list of objects")
    return rows


def maps_results(response: SerpResponse) -> list[dict]:
    rows = _objects(response.data, "local_results")
    direct = response.data.get("place_results")
    if direct is not None:
        if not isinstance(direct, dict):
            raise UpstreamError("Malformed SerpApi place_results: expected an object")
        rows = [direct, *rows]
    return rows


def _coordinates(row: dict) -> GeoPoint | None:
    gps = row.get("gps_coordinates")
    if gps is None:
        return None
    if not isinstance(gps, dict):
        raise UpstreamError("Malformed Maps coordinates")
    try:
        return GeoPoint(lat=gps["latitude"], lng=gps["longitude"])
    except (KeyError, ValidationError) as exc:
        raise UpstreamError("Malformed Maps coordinates") from exc


def locality_center(response: SerpResponse, place: Locality) -> tuple[GeoPoint | None, SourceRef]:
    aliases = {normalized_name(n) for n in (place.name, place.slug, *place.aliases)}
    source = search_source(response)
    for row in maps_results(response):
        # Reject e.g. 'Whitefield Dental Clinic' as a geocode for Whitefield.
        title = row.get("title")
        if (
            isinstance(title, str)
            and normalized_name(title) in aliases
            and (point := _coordinates(row))
        ):
            return point, source.model_copy(update={"title": title})
    return None, source


def distance_km(a: GeoPoint, b: GeoPoint) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat, dlng = lat2 - lat1, math.radians(b.lng - a.lng)
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return round(6371.0088 * 2 * math.asin(math.sqrt(min(1, value))), 2)


class _Place(BaseModel):
    title: str = Field(min_length=1)
    rating: float | None = Field(default=None, ge=0, le=5)
    reviews: int | None = Field(default=None, ge=0)
    place_id: str | None = None
    data_id: str | None = None
    type: str | None = None
    types: list[str] = Field(default_factory=list)


def _matches_category(place: _Place, category: AmenityCategory) -> bool:
    """Category comes from Maps place types, rather than a misleading business/station name."""
    words = normalized_name(" ".join([place.type or "", *place.types]))
    expected = {
        AmenityCategory.METRO: ("subway station", "metro station"),
        AmenityCategory.SCHOOL: ("school", "kindergarten", "educational institution"),
        AmenityCategory.HOSPITAL: ("hospital", "medical center", "medical centre"),
    }
    return any(term in words for term in expected[category])


def normalize_amenities(
    response: SerpResponse, category: AmenityCategory, center: GeoPoint | None, place: Locality
) -> list[Amenity]:
    results, seen = [], set()
    for row in maps_results(response):
        try:
            parsed = _Place.model_validate(row)
        except ValidationError as exc:
            raise UpstreamError("Malformed Maps amenity: title, rating or reviews") from exc
        if not _matches_category(parsed, category):
            continue
        point = _coordinates(row)
        distance = distance_km(center, point) if center is not None and point is not None else None
        if distance is not None and distance > AMENITY_RADIUS_KM:
            continue
        if distance is None and not mentions_locality(
            f"{parsed.title} {row.get('address', '')}", place
        ):
            continue
        identity = (
            parsed.place_id
            or parsed.data_id
            or (
                normalized_name(parsed.title),
                point.lat if point else None,
                point.lng if point else None,
            )
        )
        if identity in seen:
            continue
        seen.add(identity)
        url = "https://www.google.com/maps/search/?api=1&query=" + quote(parsed.title)
        if row.get("place_id"):
            url += "&query_place_id=" + quote(str(row["place_id"]))
        results.append(
            Amenity(
                name=parsed.title,
                category=category,
                location=point,
                distance_km=distance,
                rating=parsed.rating,
                reviews=parsed.reviews,
                source=SourceRef(
                    engine=response.engine,
                    url=url,
                    title=parsed.title,
                    search_id=response.search_id,
                ),
            )
        )
    return sorted(results, key=lambda r: (r.distance_km is None, r.distance_km or 0, r.name))[
        :MAX_AMENITIES
    ]


def normalize_news(response: SerpResponse, place: Locality) -> list[NewsItem]:
    pending = list(_objects(response.data, "news_results"))
    results, seen_urls, seen_titles = [], set(), set()
    while pending:
        row = pending.pop(0)
        pending.extend(_objects(row, "stories"))
        if "highlight" in row:
            if not isinstance(row["highlight"], dict):
                raise UpstreamError("Malformed News highlight")
            pending.append(row["highlight"])
        # Story-group headers without links are not articles.
        if "link" not in row:
            continue
        title, url = row.get("title"), http_url(row.get("link"))
        snippet = row.get("snippet")
        if not isinstance(title, str) or not title.strip() or url is None:
            raise UpstreamError("Malformed News article: expected title and HTTP(S) link")
        if snippet is not None and not isinstance(snippet, str):
            raise UpstreamError("Malformed News snippet")
        if not mentions_locality(title + " " + (snippet or ""), place):
            continue
        parts = urlsplit(url)
        identity = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
        title_key = normalized_name(title)
        if identity in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(identity)
        seen_titles.add(title_key)
        published = None
        if raw_date := row.get("iso_date"):
            try:
                published = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00")).date()
            except ValueError as exc:
                raise UpstreamError("Malformed News iso_date") from exc
        publication = row.get("source")
        outlet = publication.get("name") if isinstance(publication, dict) else publication
        if outlet is not None and not isinstance(outlet, str):
            raise UpstreamError("Malformed News publication")
        results.append(
            NewsItem(
                title=title,
                url=url,
                snippet=snippet,
                outlet=outlet,
                published_on=published,
                published_text=str(row["date"]) if row.get("date") else None,
                source=SourceRef(
                    engine=response.engine, url=url, title=title, search_id=response.search_id
                ),
            )
        )
    return results[:MAX_NEWS]
