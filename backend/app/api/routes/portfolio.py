from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession
from app.schemas.holding import Holding, HoldingIn, PortfolioSummary
from app.schemas.views import CompareResult, SavedProperty, SaveRequest
from app.services import holdings, portfolio

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
def portfolio_summary(db: DbSession) -> PortfolioSummary:
    return holdings.summary(db)


@router.post("/portfolio", status_code=status.HTTP_201_CREATED)
def add_holding(data: HoldingIn, db: DbSession) -> Holding:
    return holdings.save_holding(db, data)


@router.put("/portfolio/{holding_id}")
def update_holding(holding_id: str, data: HoldingIn, db: DbSession) -> Holding:
    return holdings.save_holding(db, data, holding_id)


@router.delete("/portfolio/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holding(holding_id: str, db: DbSession) -> None:
    holdings.delete_holding(db, holding_id)


@router.get("/saved")
def list_saved(db: DbSession) -> list[SavedProperty]:
    return portfolio.list_saved(db)


@router.post("/saved", status_code=status.HTTP_201_CREATED)
def save(request: SaveRequest, db: DbSession) -> SavedProperty:
    return portfolio.save(db, request)


@router.delete("/saved/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsave(listing_id: str, db: DbSession) -> None:
    portfolio.unsave(db, listing_id)


@router.get("/compare")
def compare(
    db: DbSession, ids: Annotated[list[str], Query(min_length=2, max_length=4)]
) -> CompareResult:
    return portfolio.compare(db, ids)
