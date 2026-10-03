from fastapi import APIRouter

from app.api.deps import AppSettings, DbSession
from app.schemas.views import BudgetStatus, ProfileOptions
from app.services import budget, profiles

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/budget")
def get_budget(db: DbSession, settings: AppSettings) -> BudgetStatus:
    return budget.get_budget_status(db, settings)


@router.get("/profile-options")
def get_profile_options(settings: AppSettings, city: str | None = None) -> ProfileOptions:
    """Choices for the profile form: segments and property types, localities, goals, risk."""
    return profiles.profile_options(city or settings.default_city)
