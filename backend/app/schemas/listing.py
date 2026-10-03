"""Search hits, cleaned listings, and the LLM's verification of each listing."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import GeoPoint, Level, SerpEngine
from app.schemas.profile import PropertyType, Segment
from app.schemas.provenance import Sourced, SourceRef


class Portal(StrEnum):
    NINETY_NINE_ACRES = "99acres"
    MAGICBRICKS = "magicbricks"
    HOUSING = "housing"
    NOBROKER = "nobroker"
    SQUARE_YARDS = "squareyards"
    GOOGLE_MAPS = "google_maps"
    OTHER = "other"


class ResultKind(StrEnum):
    """What a search hit actually points at.

    Portals rank aggregate pages ("312 flats for sale in Whitefield") above single listings, so
    each hit is classified before it is treated as a property. Aggregate pages still feed area
    price statistics.
    """

    LISTING = "listing"  # one specific property
    PROJECT = "project"  # a builder project page with several units
    AGGREGATE = "aggregate"  # a search or category page
    OTHER = "other"


class RawSearchHit(BaseModel):
    """One organic or local result as returned by SerpApi, before cleaning."""

    engine: SerpEngine
    query: str
    position: int | None = None
    title: str
    link: str | None = None
    snippet: str | None = None
    rich_snippet: dict[str, Any] | None = None  # SerpApi rich_snippet / extensions, verbatim
    gps: GeoPoint | None = None  # present on google_maps local results
    search_id: str | None = None
    fetched_at: datetime


class Listing(BaseModel):
    """A cleaned, de-duplicated property candidate. Every factual field is `Sourced`."""

    id: str
    canonical_url: str
    portal: Portal
    kind: ResultKind
    title: str
    segment: Segment
    property_type: Sourced[PropertyType]
    price_inr: Sourced[int]
    size_sqft: Sourced[float]
    bedrooms: Sourced[int]
    locality: Sourced[str]
    location: Sourced[GeoPoint]
    amenities: Sourced[list[str]]
    posted_on: Sourced[date]
    sources: list[SourceRef] = Field(default_factory=list)  # every hit merged into this listing
    first_seen_at: datetime
    last_seen_at: datetime


class QualityFlagKind(StrEnum):
    STALE = "stale"
    DUPLICATE = "duplicate"
    TOO_GOOD_TO_BE_TRUE = "too_good_to_be_true"
    MISSING_PRICE = "missing_price"
    MISSING_SIZE = "missing_size"
    NOT_A_LISTING = "not_a_listing"
    LOCATION_MISMATCH = "location_mismatch"


class QualityFlag(BaseModel):
    kind: QualityFlagKind
    severity: Level
    reason: str


class MatchVerdict(StrEnum):
    STRONG = "strong"
    PARTIAL = "partial"
    WEAK = "weak"
    REJECT = "reject"


class Verification(BaseModel):
    """The LLM's judgement of one listing against one investor profile (CHECKLIST F-03)."""

    listing_id: str
    match_score: int = Field(ge=0, le=100)
    verdict: MatchVerdict
    matched_criteria: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    flags: list[QualityFlag] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    model: str
