"""Search hits, discovered property candidates, and the LLM's verification of each.

Shaped by spike S-01 (docs/spikes/S-01-data-coverage.md, ADR 0011): Google returns the portals'
search pages, never single listings, so a candidate is a priced entry quoted in a search page's
snippet, or a named housing project from Google Maps.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.common import GeoPoint, Level, SerpEngine
from app.schemas.profile import PropertyType, Segment
from app.schemas.provenance import Sourced, SourceRef


class Portal(StrEnum):
    """Where a candidate came from: one of the searched portals, or Google Maps."""

    NINETY_NINE_ACRES = "99acres"
    MAGICBRICKS = "magicbricks"
    NOBROKER = "nobroker"
    GOOGLE_MAPS = "google_maps"


class ResultKind(StrEnum):
    SNIPPET_ENTRY = "snippet_entry"  # a priced entry quoted in a portal search page's snippet
    PROJECT = "project"  # a named housing project from Google Maps, no price quoted


class SaleStatus(StrEnum):
    READY_TO_MOVE = "ready_to_move"
    UNDER_CONSTRUCTION = "under_construction"
    RESALE = "resale"
    NEW_LAUNCH = "new_launch"


class RawSearchHit(BaseModel):
    """One organic (portal page) or Maps result as returned by SerpApi, before cleaning."""

    engine: SerpEngine
    query: str
    locality: str  # slug of the locality this search was for
    property_type: PropertyType  # the type this search was for
    position: int | None = None
    title: str
    link: str | None = None
    snippet: str | None = None
    # Google Maps places only
    gps: GeoPoint | None = None
    place_type: str | None = None
    address: str | None = None
    rating: float | None = None
    reviews: int | None = None
    place_id: str | None = None
    search_id: str | None = None
    fetched_at: datetime


class Listing(BaseModel):
    """A discovered, de-duplicated property candidate. Every factual field is `Sourced`."""

    id: str  # stable hash of the candidate's identity, the same in every run
    kind: ResultKind
    portal: Portal
    name: str  # project name, or the entry's own headline, e.g. "4 BHK Flat For Sale In Whitefield"
    url: str | None = None  # the portal search page it was quoted on, or its Google Maps place
    segment: Segment
    property_type: Sourced[PropertyType]
    locality: Sourced[str]  # locality slug
    price_inr: Sourced[int]
    price_per_sqft: Sourced[float]
    size_sqft: Sourced[float]
    bedrooms: Sourced[int]
    status: Sourced[SaleStatus]
    location: Sourced[GeoPoint]
    rating: float | None = None  # Google Maps rating, for projects
    reviews: int | None = None
    evidence: str | None = None  # the snippet text this candidate was parsed from
    sources: list[SourceRef] = Field(default_factory=list)  # every hit merged into this candidate
    first_seen_at: datetime
    last_seen_at: datetime


class QualityFlagKind(StrEnum):
    # No "stale" flag: search results carry no posted dates (S-01).
    DUPLICATE = "duplicate"
    TOO_GOOD_TO_BE_TRUE = "too_good_to_be_true"
    MISSING_PRICE = "missing_price"
    MISSING_SIZE = "missing_size"
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
