"""Ranked recommendations (CHECKLIST F-04)."""

from pydantic import BaseModel, Field

from app.schemas.listing import Listing, Verification
from app.schemas.metrics import InvestmentMetrics


class Recommendation(BaseModel):
    rank: int = Field(ge=1)
    listing: Listing
    verification: Verification
    metrics: InvestmentMetrics | None = None
    score: float = Field(ge=0, le=100)  # composite of match, metrics and area signals
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    reason: str  # plain-language "why this one", grounded in sourced fields
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
