"""Area intelligence for one locality (CHECKLIST F-05).

Keyed by locality, not by property: every listing in Whitefield shares one `AreaIntel`, which
keeps enrichment inside the search budget. See docs/decisions/0006-locality-keyed-enrichment.md.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import GeoPoint, Level
from app.schemas.profile import PropertyType
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
    published_text: str | None = None  # the provider's own date text, e.g. "2 days ago"
    snippet: str | None = None
    topic: NewsTopic = NewsTopic.OTHER
    sentiment: Sentiment = Sentiment.NEUTRAL
    classified: bool = False  # topic and sentiment were set by `classify_news` (ADR 0020)
    source: SourceRef


class Commute(BaseModel):
    """Driving time from the locality centre to one job hub, leaving on a weekday at 9 AM, as
    Google Maps quotes it with its usual traffic (F-23, ADR 0026). Display only."""

    hub_slug: str
    hub: str  # display name, e.g. "Manyata Tech Park"
    hub_location: GeoPoint | None = None  # from the directions response, never hand-entered
    depart_at: datetime  # the pinned departure, as Bengaluru wall-clock time
    duration_min: Sourced[int]  # Google's route time for that departure
    typical_min: int | None = None  # Google's "typically 55 min to 1 hr 50 min" range
    typical_max: int | None = None
    typical_text: str | None = None  # the range as quoted, kept when it cannot be parsed
    distance_km: float
    via: str | None = None  # e.g. "ITPL Main Rd and NH 44"


class TrendPoint(BaseModel):
    period: str  # e.g. "2026-09" or "Q3 2026"
    value: float


class RentalDemand(BaseModel):
    typical_monthly_rent_inr: Sourced[int]
    search_interest: list[TrendPoint] = Field(default_factory=list)  # Google Trends series
    signal: Level


class AreaIssue(BaseModel):
    """One part of an area that could not be loaded; shown to the investor, never hidden as empty
    (ADR 0019, after gscode007's F-05 branch)."""

    # "centre", "metro", "school", "hospital", "growth", "summary", "rent:office", "commute:manyata"
    section: str
    provider: str  # "serpapi", "deepseek" or "serpapi+deepseek"
    code: str  # the AppError code, e.g. "replay_miss", "upstream_error"
    message: str


class AreaIntel(BaseModel):
    locality_key: str  # normalised slug; the cache key
    locality: str
    city: str
    center: GeoPoint | None = None  # geocoded once per TTL (I-12)
    amenities: list[Amenity] = Field(default_factory=list)  # nearest metro, schools, hospitals
    news: list[NewsItem] = Field(default_factory=list)  # newest first; display only (ADR 0020)
    # Past-12-month change quoted in search results; for F-09's price-growth ROI. Never a forecast,
    # and null (not zero) when no result states it (ADR 0010).
    price_growth_pct: Sourced[float] | None = None
    # Sale price per sq ft by property type, from runs' price-level lookups (ADR 0014).
    price_levels: dict[PropertyType, Sourced[float]] = Field(default_factory=dict)
    # Monthly rent per sq ft by property type: median of quoted rent ÷ size pairs (ADR 0017).
    rent_levels: dict[PropertyType, Sourced[float]] = Field(default_factory=dict)
    # Drive to each job hub by hub slug, weekday 9 AM, from the centre (F-23); display only.
    commutes: dict[str, Commute] = Field(default_factory=dict)
    rental_demand: RentalDemand | None = None  # not collected yet (F-05 P1)
    summary: str | None = None
    infrastructure_summary: str | None = None
    summary_by_ai: bool = False  # True when the summaries passed the number check (ADR 0016)
    # "ok": data found; "empty": the search worked but found nothing; "failed": see `warnings`.
    section_status: dict[str, Literal["ok", "empty", "failed"]] = Field(default_factory=dict)
    warnings: list[AreaIssue] = Field(default_factory=list)
    # A cached area is reused only when both match the running code and providers (ADR 0019).
    schema_version: int = 1
    provider_modes: dict[str, str] = Field(default_factory=dict)
    fetched_at: datetime
    expires_at: datetime  # equals fetched_at when a section failed, so the next run retries


class AreaAccess(BaseModel):
    """Distances from a listing (or its locality centre) to the area's amenities, in code."""

    metro_name: str | None = None
    metro_km: float | None = None
    schools_3km: int = 0
    hospitals_3km: int = 0
    measured_from: Literal["listing", "locality centre"]
