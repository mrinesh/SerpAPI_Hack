"""Search budget status for the UI (CHECKLIST I-05): our ledger plus the SerpApi Account API."""

from sqlalchemy.orm import Session

from app.config import Settings
from app.core.errors import NotImplementedYet
from app.schemas.views import BudgetStatus


def get_budget_status(db: Session, settings: Settings) -> BudgetStatus:
    raise NotImplementedYet("I-05", "Search budget status")
