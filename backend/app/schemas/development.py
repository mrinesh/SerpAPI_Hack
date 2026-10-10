"""Measured locality momentum, observed corroboration and explicitly unconfirmed causes."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.area import AreaIssue
from app.schemas.forecast import TrendForecast
from app.schemas.provenance import Sourced, SourceRef


class InterestPoint(BaseModel):
    week: date
    value: float = Field(ge=0)


class SearchMomentum(BaseModel):
    kind: Literal["locality_interest", "rental_interest", "app_searches"]
    query: str
    unit: Literal["relative_interest_0_100", "distinct_profiles_per_week"]
    geo: str | None = None
    history: list[InterestPoint] = Field(default_factory=list)
    previous_mean: float | None = None
    recent_mean: float | None = None
    quarter_change_pct: float | None = None
    annual_change_pct: float | None = None
    sustained_weeks: int = 0
    signal: Literal["rising", "falling", "steady", "unavailable"] = "unavailable"
    usable: bool = False
    note: str
    source: SourceRef | None = None
    retrieved_at: str | None = None
    sample_size: int | None = None


class DevelopmentHypothesis(BaseModel):
    driver: Literal["transport", "employment", "housing", "policy", "amenities", "publicity"]
    explanation: str
    evidence: Sourced[str]


class AreaDevelopment(BaseModel):
    forecasts: list[TrendForecast] = Field(default_factory=list)
    locality_key: str
    locality: str
    city: str
    as_of: datetime
    public_interest: list[SearchMomentum] = Field(default_factory=list)
    app_interest: SearchMomentum
    observed_price_growth: dict[str, Sourced[float]] = Field(default_factory=dict)
    recent_positive_infrastructure: int = 0
    evidence_score: float | None = None
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    coverage_pct: float = 0
    signal: Literal[
        "corroborated_growth", "interest_only", "no_sustained_growth", "insufficient_data"
    ]
    recommendation: str
    rank: int | None = None
    hypotheses: list[DevelopmentHypothesis] = Field(default_factory=list)
    ai_review: Literal["consistent", "mixed", "inconclusive", "unavailable"] = "unavailable"
    warnings: list[AreaIssue] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
