"""Investor profile: the criteria every pipeline run starts from (CHECKLIST F-01)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Segment(StrEnum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"


class PropertyType(StrEnum):
    APARTMENT = "apartment"
    VILLA = "villa"
    INDEPENDENT_HOUSE = "independent_house"
    PLOT = "plot"
    OFFICE = "office"
    RETAIL = "retail"
    WAREHOUSE = "warehouse"


class RiskAppetite(StrEnum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class InvestmentGoal(StrEnum):
    RENTAL_INCOME = "rental_income"
    APPRECIATION = "appreciation"
    BALANCED = "balanced"


class ROIMeasure(StrEnum):
    """What the profile's target ROI is compared against (docs/decisions/0010-roi-definition.md)."""

    RENTAL_YIELD = "rental_yield"  # annual rent / price, before costs
    PRICE_GROWTH = "price_growth"  # past-12-month locality change, or the investor's override
    TOTAL_RETURN = "total_return"  # rental yield + price growth


GOAL_MEASURE: dict[InvestmentGoal, ROIMeasure] = {
    InvestmentGoal.RENTAL_INCOME: ROIMeasure.RENTAL_YIELD,
    InvestmentGoal.APPRECIATION: ROIMeasure.PRICE_GROWTH,
    InvestmentGoal.BALANCED: ROIMeasure.TOTAL_RETURN,
}


class InvestorProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    segment: Segment
    property_types: list[PropertyType] = Field(min_length=1)
    city: str = "Bengaluru"
    localities: list[str] = Field(default_factory=list)  # empty means anywhere in the city
    budget_min_inr: int | None = Field(default=None, ge=0)
    budget_max_inr: int = Field(gt=0)
    size_min_sqft: int | None = Field(default=None, gt=0)
    size_max_sqft: int | None = Field(default=None, gt=0)
    bedrooms: list[int] = Field(default_factory=list)  # residential only, e.g. [2, 3]
    target_yield_pct: float | None = Field(default=None, ge=0, le=100)  # target gross yield
    risk_appetite: RiskAppetite = RiskAppetite.BALANCED
    goal: InvestmentGoal = InvestmentGoal.BALANCED
    # Commercial only: the business a tenant would run there (e.g. "cafe", "pharmacy").
    # Drives competitor analysis.
    business_category: str | None = None
    must_haves: list[str] = Field(default_factory=list)  # free text, e.g. "near metro"

    @model_validator(mode="after")
    def _check_ranges(self) -> "InvestorProfileIn":
        if self.budget_min_inr is not None and self.budget_min_inr > self.budget_max_inr:
            raise ValueError("budget_min_inr must not exceed budget_max_inr")
        if (
            self.size_min_sqft is not None
            and self.size_max_sqft is not None
            and self.size_min_sqft > self.size_max_sqft
        ):
            raise ValueError("size_min_sqft must not exceed size_max_sqft")
        return self


class InvestorProfile(InvestorProfileIn):
    id: str
    created_at: datetime
    updated_at: datetime
