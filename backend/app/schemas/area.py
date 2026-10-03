"""Area intelligence for one locality (CHECKLIST F-05).

Keyed by locality, not by property: every listing in Whitefield shares one `AreaIntel`, which
keeps enrichment inside the search budget. See docs/decisions/0006-locality-keyed-enrichment.md.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.common import GeoPoint, Level
from app.schemas.provenance import Sourced, SourceRef


class AmenityCategory(StrEnum):
    METRO = "metro"
    BUS = "bus"
    SCHOOL = "school"
    HOSPITAL = "hospital"
    MALL = "mall"
    SUPERMARKET = "supermarket"
    PARK = "park"
    TECH_PARK = "tech_park"
    OTHER = "other"


class Amenity(BaseModel):
    name: str
    category: AmenityCategory
    location: GeoPoint | None = None
    distance_km: float | None = None
    rating: float | None = None
    reviews: int | None = None
    source: SourceRef


class NewsTopic(StrEnum):
    INFRASTRUCTURE = "infrastructure"
    MARKET = "market"
    POLICY = "policy"
    CIVIC = "civic"
    OTHER = "other"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class NewsItem(BaseModel):
    title: str
    url: str
    outlet: str | None = None
    published_on: date | None = None
    snippet: str | None = None
    topic: NewsTopic = NewsTopic.OTHER
    sentiment: Sentiment = Sentiment.NEUTRAL
    source: SourceRef


class TrendPoint(BaseModel):
    period: str  # e.g. "2026-09" or "Q3 2026"
    value: float


class PriceTrend(BaseModel):
    avg_price_per_sqft: Sourced[float]
    yoy_change_pct: Sourced[float]
    history: list[TrendPoint] = Field(default_factory=list)


class RentalDemand(BaseModel):
    typical_monthly_rent_inr: Sourced[int]
    search_interest: list[TrendPoint] = Field(default_factory=list)  # Google Trends series
    signal: Level


class AreaIntel(BaseModel):
    locality_key: str  # normalised slug; the cache key
    locality: str
    city: str
    center: GeoPoint | None = None
    amenities: list[Amenity] = Field(default_factory=list)
    news: list[NewsItem] = Field(default_factory=list)
    infrastructure_summary: Sourced[str] | None = None
    price_trend: PriceTrend | None = None
    rental_demand: RentalDemand | None = None
    summary: str | None = None
    fetched_at: datetime
    expires_at: datetime
