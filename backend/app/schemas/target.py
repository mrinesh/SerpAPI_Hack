"""Suggested target ROI for a profile being written (ADR 0018)."""

from pydantic import BaseModel, Field

from app.schemas.profile import (
    MAX_LOCALITIES,
    InvestmentGoal,
    PropertyType,
    RiskAppetite,
    ROIMeasure,
    Segment,
)
from app.schemas.provenance import Sourced


class TargetSuggestionIn(BaseModel):
    """The profile fields a suggestion depends on; the wizard knows them by its Money step."""

    segment: Segment
    property_types: list[PropertyType] = Field(min_length=1)
    city: str = "Bengaluru"
    localities: list[str] = Field(min_length=1, max_length=MAX_LOCALITIES)
    goal: InvestmentGoal
    risk_appetite: RiskAppetite


class TargetSuggestionPart(BaseModel):
    locality: str  # display name
    property_type: PropertyType
    typical: Sourced[float]  # the goal's measure for this locality and type, % a year


class TargetSuggestion(BaseModel):
    target_roi_pct: float | None  # None when no sourced data was found
    measure: ROIMeasure
    typical_pct: float | None  # median of the parts, before the risk adjustment
    basis: str  # one plain sentence shown under the field
    parts: list[TargetSuggestionPart] = Field(default_factory=list)
