"""Pipeline runs and their stage-by-stage progress (shown live in the UI)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PipelineStage(StrEnum):
    PLAN = "plan"  # profile -> search queries
    FETCH = "fetch"  # SerpApi discovery searches
    CLEAN = "clean"  # normalise, classify, de-duplicate
    VERIFY = "verify"  # LLM match scoring and quality flags
    ENRICH = "enrich"  # area intelligence, competitors, metrics
    RANK = "rank"  # ranked shortlist with reasons


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class StageEvent(BaseModel):
    stage: PipelineStage
    status: RunStatus
    message: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)  # e.g. {"hits": 48, "listings": 17}
    started_at: datetime | None = None
    finished_at: datetime | None = None


class PipelineRun(BaseModel):
    id: str
    profile_id: str
    status: RunStatus
    current_stage: PipelineStage | None = None
    events: list[StageEvent] = Field(default_factory=list)
    searches_used: int = 0  # live SerpApi searches charged to this run
    cache_hits: int = 0
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
