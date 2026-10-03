from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.pipeline import orchestrator
from app.schemas.profile import InvestorProfile, InvestorProfileIn
from app.schemas.run import PipelineRun
from app.services import profiles

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_profile(data: InvestorProfileIn, db: DbSession) -> InvestorProfile:
    return profiles.create_profile(db, data)


@router.get("")
def list_profiles(db: DbSession) -> list[InvestorProfile]:
    return profiles.list_profiles(db)


@router.get("/{profile_id}")
def get_profile(profile_id: str, db: DbSession) -> InvestorProfile:
    return profiles.get_profile(db, profile_id)


@router.put("/{profile_id}")
def update_profile(profile_id: str, data: InvestorProfileIn, db: DbSession) -> InvestorProfile:
    return profiles.update_profile(db, profile_id, data)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: str, db: DbSession) -> None:
    profiles.delete_profile(db, profile_id)


@router.post("/{profile_id}/runs", status_code=status.HTTP_202_ACCEPTED)
def start_run(profile_id: str) -> PipelineRun:
    """Start the search -> verify -> enrich -> rank pipeline. Poll GET /api/runs/{id}."""
    return orchestrator.start_run(profile_id)
