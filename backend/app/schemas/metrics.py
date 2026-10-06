"""Investment metrics (CHECKLIST F-09): what makes this an investor tool, not a listing feed.

ROI is measured three ways and the profile's goal picks which one its target is compared to
(docs/decisions/0010-roi-definition.md). No net yield or cap rate: they need cost assumptions.
"""

from pydantic import BaseModel

from app.schemas.profile import ROIMeasure
from app.schemas.provenance import Sourced


class InvestmentMetrics(BaseModel):
    price_per_sqft: Sourced[float]
    area_avg_price_per_sqft: Sourced[float]
    price_vs_area_pct: Sourced[float]  # +12 means 12% above the locality average
    est_monthly_rent_inr: Sourced[int]
    rental_yield_pct: Sourced[float]  # annual rent / price, before any costs
    price_growth_pct: Sourced[float]  # locality's past-12-month change, or the investor's override
    total_return_pct: Sourced[float]  # rental yield + price growth
    roi_measure: ROIMeasure  # which of the three the profile's target ROI is compared against
    meets_target_roi: bool | None = None  # None when the measured value is missing
    # Frozen at computation, so editing the profile later does not change an old verdict.
    target_roi_pct: float | None = None
    assessment_note: str | None = None  # why there is no verdict, when there is none (ADR 0019)
