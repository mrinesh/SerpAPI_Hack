from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.provenance import SourceRef


class ForecastPoint(BaseModel):
    week: date
    value: float
    lower: float
    upper: float


class TrendForecast(BaseModel):
    kind: str
    status: Literal["projected", "unavailable"]
    as_of: date
    observations: int = 0
    holdout_mae: float | None = None
    points: list[ForecastPoint] = Field(default_factory=list)
    source: SourceRef | None = None
    note: str
