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
    # Points each component contributed, plus `flag_penalty` (negative); None = not available
    # yet (ROI until F-09, area signals until F-05). See docs/decisions/0015-composite-ranking.md.
    score_breakdown: dict[str, float | None] = Field(default_factory=dict)
    reason: str  # plain-language "why this one", grounded in sourced fields
    highlights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    explained: bool = False  # True when `reason` was written by the LLM and passed the number check
