"""Competitor analysis for commercial properties (CHECKLIST F-06)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import GeoPoint, Level
from app.schemas.provenance import Sourced, SourceRef


class Competitor(BaseModel):
    name: str
    category: str
    location: GeoPoint | None = None
    distance_km: float | None = None
    rating: float | None = None
    reviews: int | None = None
    price_level: str | None = None
    place_id: str | None = None
    data_id: str | None = None  # needed for the google_maps_reviews engine
    source: SourceRef


class CompetitorReport(BaseModel):
    category: str
    center: GeoPoint
    radius_km: float
    competitors: list[Competitor] = Field(default_factory=list)
    density_per_sq_km: float
    avg_rating: float | None = None
    total_reviews: int = 0
    saturation: Level
    gaps: list[Sourced[str]] = Field(default_factory=list)  # market gaps, each with citations
    fetched_at: datetime
