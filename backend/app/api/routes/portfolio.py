from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession
from app.schemas.views import CompareResult, SavedProperty, SaveRequest
from app.services import portfolio

router = APIRouter(tags=["portfolio"])


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
