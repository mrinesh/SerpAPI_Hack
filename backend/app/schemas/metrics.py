"""Investment metrics (CHECKLIST F-09): what makes this an investor tool, not a listing feed."""

from pydantic import BaseModel, Field

from app.schemas.provenance import Sourced


class InvestmentMetrics(BaseModel):
    price_per_sqft: Sourced[float]
    area_avg_price_per_sqft: Sourced[float]
    price_vs_area_pct: Sourced[float]  # +12 means 12% above the locality average
    est_monthly_rent_inr: Sourced[int]
    gross_yield_pct: Sourced[float]
    net_yield_pct: Sourced[float]
    cap_rate_pct: Sourced[float]  # commercial: net operating income / price
    meets_target_yield: bool | None = None
    # Every assumption used (vacancy, maintenance, property tax...) so the UI can show them.
    assumptions: dict[str, float] = Field(default_factory=dict)
