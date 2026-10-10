"""Evidence screening, not a certified hazard or title assessment (F-13)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.provenance import SourceRef


class RiskIndicator(BaseModel):
    kind: Literal["flood", "legal", "oversupply"]
    status: Literal["reported_concern", "unknown"]
    score: int | None = None
    evidence: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    next_step: str


class RiskReport(BaseModel):
    indicators: list[RiskIndicator]
    reported_concern_score: float | None = None
    coverage_pct: float
    note: str
