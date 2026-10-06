from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.listing import Listing, Verification
from app.schemas.recommendation import Recommendation
from app.schemas.run import PipelineRun
from app.services import runs

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}")
def get_run(run_id: str, db: DbSession) -> PipelineRun:
    return runs.get_run(db, run_id)


@router.get("/{run_id}/listings")
def get_run_listings(run_id: str, db: DbSession) -> list[Listing]:
    """All candidates from this run, including extraction additions and rejected candidates."""
    return runs.get_run_listings(db, run_id)


@router.get("/{run_id}/verifications")
def get_run_verifications(run_id: str, db: DbSession) -> list[Verification]:
    """Completed relevance checks (F-03), including reasons for rejection."""
    return runs.get_verifications(db, run_id)


@router.get("/{run_id}/recommendations")
def get_recommendations(run_id: str, db: DbSession) -> list[Recommendation]:
    return runs.get_recommendations(db, run_id)
