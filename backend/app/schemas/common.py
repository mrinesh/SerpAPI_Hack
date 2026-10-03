"""Small shared types."""

from enum import StrEnum

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class SerpEngine(StrEnum):
    """SerpApi engines the platform uses. See docs/SERPAPI_USAGE.md for what each one does."""

    GOOGLE = "google"
    GOOGLE_MAPS = "google_maps"
    GOOGLE_MAPS_REVIEWS = "google_maps_reviews"
    GOOGLE_NEWS = "google_news"
    GOOGLE_TRENDS = "google_trends"


class Level(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
