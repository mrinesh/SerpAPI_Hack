"""Response shapes that combine domain objects for specific screens."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.config import ProviderMode
from app.schemas.area import AreaIntel
from app.schemas.competitor import CompetitorReport
from app.schemas.listing import Listing, Verification
from app.schemas.metrics import InvestmentMetrics
from app.schemas.profile import ROIMeasure
from app.schemas.provenance import SourceRef
from app.schemas.recommendation import Recommendation


class HealthStatus(BaseModel):
    status: str
    version: str
    serpapi_mode: ProviderMode
    llm_mode: ProviderMode
    city: str


class BudgetStatus(BaseModel):
    serpapi_mode: ProviderMode
    monthly_budget: int
    used_this_month: int  # from our own search ledger
    cache_hits_this_month: int
    account_searches_left: int | None = None  # from the SerpApi Account API (free to call)


class Option(BaseModel):
    value: str
    label: str


class SegmentOption(Option):
    property_types: list[Option]


class GoalOption(Option):
    measure: ROIMeasure  # what the target ROI is compared against for this goal
    measure_label: str


class LocalityOption(BaseModel):
    slug: str
    name: str


class ProfileOptions(BaseModel):
    """Everything the profile form offers, so the UI never hard-codes choices (CHECKLIST F-01)."""

    city: str
    segments: list[SegmentOption]
    localities: list[LocalityOption]
    locality_source: str
    max_localities: int
    business_type_suggestions: list[str]
    goals: list[GoalOption]
    risk_levels: list[Option]


class PriceObservation(BaseModel):
    """The price a listing was quoted at when one run saw it."""

    run_id: str
    price_inr: int | None = None
    seen_at: datetime


class PropertyDetail(BaseModel):
    """Everything known about one property as one run judged it, for the detail page
    (CHECKLIST F-07). Run-scoped because the verdict, metrics and score belong to that run's
    profile and are frozen with it (docs/decisions/0021-run-scoped-property-detail.md)."""

    run_id: str
    profile_id: str
    listing: Listing
    verification: Verification | None = None  # None until checked, or past the check cap
    recommendation: Recommendation | None = None  # None unless ranked (rejects never are)
    metrics: InvestmentMetrics | None = None
    area: AreaIntel | None = None  # the area this run used for the listing's locality
    competitors: CompetitorReport | None = None  # commercial only, from F-06
    price_history: list[PriceObservation] = Field(default_factory=list)  # every run, oldest first
    # Every source behind the figures above, de-duplicated (F-11); news is display only.
    sources: list[SourceRef] = Field(default_factory=list)


class CompareResult(BaseModel):
    properties: list[PropertyDetail] = Field(min_length=2, max_length=4)


class SaveRequest(BaseModel):
    listing_id: str
    note: str | None = None


class SavedProperty(BaseModel):
    listing: Listing
    note: str | None = None
    saved_at: datetime


class AlertKind(StrEnum):
    NEW_MATCH = "new_match"
    PRICE_DROP = "price_drop"


class Alert(BaseModel):
    id: str
    profile_id: str
    kind: AlertKind
    listing_id: str
    message: str
    created_at: datetime
    read_at: datetime | None = None
