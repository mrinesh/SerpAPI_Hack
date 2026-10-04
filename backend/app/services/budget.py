"""Search budget status for the UI (CHECKLIST I-05): our ledger plus the SerpApi Account API."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import ProviderMode, Settings
from app.core.errors import AppError
from app.db.models import SearchLedgerRow
from app.integrations.serpapi.gateway import SerpApiGateway, month_start
from app.schemas.views import BudgetStatus


def get_budget_status(
    db: Session, settings: Settings, gateway: SerpApiGateway | None = None
) -> BudgetStatus:
    gateway = gateway or SerpApiGateway(settings, db)
    since = month_start()
    cached = db.scalar(
        select(func.count())
        .select_from(SearchLedgerRow)
        .where(~SearchLedgerRow.live, SearchLedgerRow.created_at >= since)
    )
    searches_left = None
    # The Account API is free, but replay mode promises no network at all.
    if settings.serpapi_api_key and settings.serpapi_mode is not ProviderMode.REPLAY:
        try:
            searches_left = gateway.account().get("total_searches_left")
        except AppError:
            searches_left = None
    return BudgetStatus(
        serpapi_mode=settings.serpapi_mode,
        monthly_budget=settings.serpapi_monthly_budget,
        used_this_month=gateway.live_searches(since=since),
        cache_hits_this_month=cached or 0,
        account_searches_left=searches_left,
    )
