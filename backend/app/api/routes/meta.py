from fastapi import APIRouter

from app.api.deps import AppSettings, DbSession
from app.schemas.views import BudgetStatus
from app.services import budget

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/budget")
def get_budget(db: DbSession, settings: AppSettings) -> BudgetStatus:
    return budget.get_budget_status(db, settings)
