"""Static market reference data: localities and UI suggestions, one JSON file per city.

Only cities listed in `MARKET_FILES` are supported; the city name never becomes a file path.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

_DIR = Path(__file__).parent

MARKET_FILES: dict[str, str] = {"bengaluru": "bengaluru.json"}


class Locality(BaseModel):
    slug: str
    name: str
    aliases: list[str] = Field(default_factory=list)


class Bounds(BaseModel):
    """A loose box around the city, used only to reject geocoding results from elsewhere."""

    south: float
    west: float
    north: float
    east: float

    def contains(self, lat: float, lng: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lng <= self.east


class Market(BaseModel):
    city: str
    city_aliases: list[str]
    query_city_name: str  # the city word used in search queries; "Bangalore" was tested in S-01
    serpapi_location: str
    trends_geo: str
    locality_source: str
    localities: list[Locality]
    business_type_suggestions: list[str]
    bounds: Bounds | None = None

    def locality(self, slug: str) -> Locality | None:
        return next((loc for loc in self.localities if loc.slug == slug), None)


@lru_cache
def load_market(city: str) -> Market | None:
    """The market for `city` (case-insensitive), or None when the city is not supported."""
    filename = MARKET_FILES.get(city.strip().lower())
    if filename is None:
        return None
    return Market.model_validate_json((_DIR / filename).read_text(encoding="utf-8"))
