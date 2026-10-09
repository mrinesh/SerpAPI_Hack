"""Saved properties and side-by-side comparison (CHECKLIST F-08)."""

from datetime import UTC

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import InvalidInput, NotFound
from app.db.models import ListingRow, SavedPropertyRow
from app.schemas.listing import Listing
from app.schemas.views import CompareResult, SavedProperty, SaveRequest
from app.services.properties import get_property_detail


def list_saved(db: Session) -> list[SavedProperty]:
    rows = db.execute(
        select(SavedPropertyRow, ListingRow)
        .join(ListingRow, ListingRow.id == SavedPropertyRow.listing_id)
        .order_by(SavedPropertyRow.saved_at.desc(), SavedPropertyRow.listing_id)
    )
    return [_view(saved, listing) for saved, listing in rows]


def save(db: Session, request: SaveRequest) -> SavedProperty:
    listing = db.get(ListingRow, request.listing_id)
    if listing is None:
        raise NotFound(f"Property {request.listing_id} not found")
    row = db.get(SavedPropertyRow, request.listing_id)
    if row is None:
        row = SavedPropertyRow(listing_id=request.listing_id)
        db.add(row)
    row.note = request.note.strip() or None if request.note is not None else None
    db.commit()
    return _view(row, listing)


def unsave(db: Session, listing_id: str) -> None:
    db.execute(delete(SavedPropertyRow).where(SavedPropertyRow.listing_id == listing_id))
    db.commit()


def compare(db: Session, listing_ids: list[str]) -> CompareResult:
    if not 2 <= len(listing_ids) <= 4 or len(set(listing_ids)) != len(listing_ids):
        raise InvalidInput(["query", "ids"], "Select 2-4 distinct properties.")
    return CompareResult(properties=[get_property_detail(db, key) for key in listing_ids])


def _view(row: SavedPropertyRow, listing: ListingRow) -> SavedProperty:
    return SavedProperty(
        listing=Listing.model_validate(listing.data),
        note=row.note,
        saved_at=row.saved_at.replace(tzinfo=row.saved_at.tzinfo or UTC),
    )
