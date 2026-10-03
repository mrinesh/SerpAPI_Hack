"""State shared by every stage of one pipeline run."""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.llm.base import LLMProvider
from app.integrations.serpapi.gateway import SerpApiGateway
from app.schemas.profile import InvestorProfile
from app.schemas.run import StageEvent


@dataclass
class PipelineContext:
    run_id: str
    profile: InvestorProfile
    settings: Settings
    db: Session
    serp: SerpApiGateway
    llm: LLMProvider
    emit: Callable[[StageEvent], None]  # persists a progress event the UI polls for
