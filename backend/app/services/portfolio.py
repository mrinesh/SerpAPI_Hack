"""Saved properties and side-by-side comparison (CHECKLIST F-08)."""

from sqlalchemy.orm import Session

from app.core.errors import NotImplementedYet
from app.schemas.views import CompareResult, SavedProperty, SaveRequest


def list_saved(db: Session) -> list[SavedProperty]:
    raise NotImplementedYet("F-08", "Listing saved properties")


def save(db: Session, request: SaveRequest) -> SavedProperty:
    raise NotImplementedYet("F-08", "Saving a property")


def unsave(db: Session, listing_id: str) -> None:
    raise NotImplementedYet("F-08", "Removing a saved property")


def compare(db: Session, listing_ids: list[str]) -> CompareResult:
    raise NotImplementedYet("F-08", "Comparing properties")
