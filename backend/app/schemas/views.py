"""Response shapes that combine domain objects for specific screens."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.config import ProviderMode
from app.schemas.area import AreaIntel
from app.schemas.competitor import CompetitorReport
from app.schemas.listing import Listing, Verification
from app.schemas.metrics import InvestmentMetrics


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


class PropertyDetail(BaseModel):
    """Everything known about one property, for the detail page (CHECKLIST F-07)."""

    listing: Listing
    verification: Verification | None = None
    metrics: InvestmentMetrics | None = None
    area: AreaIntel | None = None
    competitors: CompetitorReport | None = None
    reason: str | None = None


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
