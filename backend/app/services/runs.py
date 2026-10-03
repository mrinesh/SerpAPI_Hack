"""Pipeline runs and their results (CHECKLIST I-09, F-04)."""

from sqlalchemy.orm import Session

from app.core.errors import NotImplementedYet
from app.schemas.recommendation import Recommendation
from app.schemas.run import PipelineRun


def get_run(db: Session, run_id: str) -> PipelineRun:
    raise NotImplementedYet("I-09", "Reading run status")


def get_recommendations(db: Session, run_id: str) -> list[Recommendation]:
    raise NotImplementedYet("F-04", "Reading ranked recommendations")
