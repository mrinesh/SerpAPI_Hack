from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.views import Alert
from app.services import alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(db: DbSession, unread_only: bool = False) -> list[Alert]:
    return alerts.list_alerts(db, unread_only=unread_only)


@router.post("/check")
def check_alerts(db: DbSession) -> list[Alert]:
    """Run the alert check now instead of waiting for the scheduler (used in the demo)."""
    return alerts.check_alerts(db)
