"""Investor profile: the criteria every pipeline run starts from (CHECKLIST F-01).

Validation here is pure (no I/O). Checks that need reference data, such as whether a locality
exists in the market, run in app/services/profiles.py.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
)

MAX_LOCALITIES = 5


class Segment(StrEnum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"


class PropertyType(StrEnum):
    """Grouped from the listing portals' own categories (NoBroker's site, 99acres), so search
    queries use the portals' vocabulary."""

    APARTMENT = "apartment"
    HOUSE_VILLA = "house_villa"
    BUILDER_FLOOR = "builder_floor"
    PLOT = "plot"
    OFFICE = "office"
    SHOP_SHOWROOM = "shop_showroom"
    WAREHOUSE = "warehouse"
    COMMERCIAL_LAND = "commercial_land"


SEGMENT_PROPERTY_TYPES: dict[Segment, tuple[PropertyType, ...]] = {
    Segment.RESIDENTIAL: (
        PropertyType.APARTMENT,
        PropertyType.HOUSE_VILLA,
        PropertyType.BUILDER_FLOOR,
        PropertyType.PLOT,
    ),
    Segment.COMMERCIAL: (
        PropertyType.OFFICE,
        PropertyType.SHOP_SHOWROOM,
        PropertyType.WAREHOUSE,
        PropertyType.COMMERCIAL_LAND,
    ),
}

PROPERTY_TYPE_LABELS: dict[PropertyType, str] = {
    PropertyType.APARTMENT: "Apartment / Flat",
    PropertyType.HOUSE_VILLA: "Independent House / Villa",
    PropertyType.BUILDER_FLOOR: "Builder Floor",
    PropertyType.PLOT: "Plot / Land",
    PropertyType.OFFICE: "Office Space",
    PropertyType.SHOP_SHOWROOM: "Shop / Showroom",
    PropertyType.WAREHOUSE: "Warehouse / Godown",
    PropertyType.COMMERCIAL_LAND: "Commercial Land",
}


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
    # Cross-field checks are field validators reading earlier fields from `info.data`, so each
    # error points at a field the UI can highlight. Field order therefore matters.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)

    # What
    segment: Segment
    property_types: list[PropertyType] = Field(min_length=1)
    size_min_sqft: int | None = Field(default=None, gt=0)
    size_max_sqft: int | None = Field(default=None, gt=0)
    # Commercial only, and required there: the business that would run in the property
    # (e.g. "cafe"). Drives competitor analysis (F-06).
    business_type: str | None = Field(default=None, max_length=60, validate_default=True)

    # Where. Locality slugs come from app/reference/<city>.json; the service checks them.
    city: str = "Bengaluru"
    localities: list[str] = Field(min_length=1, max_length=MAX_LOCALITIES)
    must_haves: list[str] = Field(default_factory=list, max_length=10)  # e.g. "near metro"

    # Money
    budget_min_inr: int | None = Field(default=None, ge=0)
    budget_max_inr: int = Field(gt=0)
    goal: InvestmentGoal
    target_roi_pct: float = Field(ge=0, le=100)  # compared against GOAL_MEASURE[goal]
    # Replaces the locality's past-12-month price change in price growth and total return.
    expected_growth_pct: float | None = Field(default=None, ge=-100, le=100)
    risk_appetite: RiskAppetite

    @field_validator("property_types")
    @classmethod
    def _types_match_segment(cls, value: list[PropertyType], info: ValidationInfo):
        if len(set(value)) != len(value):
            raise ValueError("property types must not repeat")
        segment = info.data.get("segment")
        if segment is not None:
            wrong = [t for t in value if t not in SEGMENT_PROPERTY_TYPES[segment]]
            if wrong:
                labels = ", ".join(PROPERTY_TYPE_LABELS[t] for t in wrong)
                raise ValueError(f"{labels} is not a {segment} property type")
        return value

    @field_validator("size_max_sqft")
    @classmethod
    def _size_range(cls, value: int | None, info: ValidationInfo):
        size_min = info.data.get("size_min_sqft")
        if value is not None and size_min is not None and value < size_min:
            raise ValueError("maximum size must be at least the minimum size")
        return value

    @field_validator("business_type")
    @classmethod
    def _business_type_for_commercial(cls, value: str | None, info: ValidationInfo):
        value = value or None  # an empty string means "not given"
        segment = info.data.get("segment")
        if segment is Segment.COMMERCIAL and value is None:
            raise ValueError("business type is required for commercial profiles")
        if segment is Segment.RESIDENTIAL and value is not None:
            raise ValueError("business type applies only to commercial profiles")
        return value

    @field_validator("localities")
    @classmethod
    def _unique_localities(cls, value: list[str]):
        if len(set(value)) != len(value):
            raise ValueError("localities must not repeat")
        return value

    @field_validator("must_haves")
    @classmethod
    def _non_empty_must_haves(cls, value: list[str]):
        if any(not item for item in value):
            raise ValueError("must-haves must not be empty")
        return value

    @field_validator("budget_max_inr")
    @classmethod
    def _budget_range(cls, value: int, info: ValidationInfo):
        budget_min = info.data.get("budget_min_inr")
        if budget_min is not None and value < budget_min:
            raise ValueError("maximum budget must be at least the minimum budget")
        return value


class InvestorProfile(InvestorProfileIn):
    id: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def roi_measure(self) -> ROIMeasure:
        return GOAL_MEASURE[self.goal]
