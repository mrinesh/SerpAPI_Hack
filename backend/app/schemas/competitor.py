"""Same-category businesses around a commercial locality (CHECKLIST F-06, ADR 0023).

Keyed by locality and business type, like area intelligence (ADR 0006): commercial candidates
carry no GPS of their own (S-01), so "near the property" is "near its locality's centre".
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.area import AreaIssue
from app.schemas.common import GeoPoint, Level
from app.schemas.profile import PropertyType
from app.schemas.provenance import Sourced, SourceRef


class CompetitorReading(StrEnum):
    """What nearby same-category businesses mean for one property type (ADR 0023)."""

    COMPETITION = "competition"  # shops: they compete for the same customers
    CLUSTER = "cluster"  # offices, warehouses, land: they show a business cluster and demand


class Competitor(BaseModel):
    name: str
    category: str  # the Google Maps place type, e.g. "Software company"
    location: GeoPoint | None = None
    distance_km: float | None = None  # from the locality centre, computed in code
    rating: float | None = None
    reviews: int | None = None
    place_id: str | None = None
    data_id: str | None = None  # needed for the google_maps_reviews engine (F-06b)
    source: SourceRef


class CompetitorReport(BaseModel):
    locality_key: str  # the area's key, e.g. "bengaluru/koramangala"
    locality: str
    business_type: str  # the profile's business, used as the Maps query
    center: GeoPoint
    radius_km: float
    competitors: list[Competitor] = Field(default_factory=list)  # within the radius, nearest first
    # The search returns one page of up to 20 places ranked by Google, so counts are a sample.
    results_seen: int = 0
    more_available: bool = False  # Google had a further page; the count is a floor
    density_per_sq_km: float = 0
    density_level: Level = Level.LOW  # from the count within the radius (ADR 0023)
    avg_rating: float | None = None
    total_reviews: int = 0
    readings: dict[PropertyType, CompetitorReading] = Field(default_factory=dict)
    gaps: list[Sourced[str]] = Field(default_factory=list)  # F-06b: market gaps from reviews
    # "ok": places found; "empty": the search worked but none were in range; "failed": `warning`.
    status: Literal["ok", "empty", "failed"] = "ok"
    warning: AreaIssue | None = None
    schema_version: int = 1
    provider_modes: dict[str, str] = Field(default_factory=dict)
    fetched_at: datetime
    expires_at: datetime  # equals fetched_at when the search failed, so the next run retries
