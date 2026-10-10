"""Saved properties and side-by-side comparison (CHECKLIST F-08)."""

from datetime import UTC

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import InvalidInput, NotFound
from app.db.models import ListingRow, SavedPropertyRow, UserSavedPropertyRow
from app.schemas.listing import Listing
from app.schemas.views import CompareResult, SavedProperty, SaveRequest
from app.services.access import owner_id
from app.services.properties import get_property_detail


def _model(db: Session):
    return SavedPropertyRow if owner_id(db) == "local" else UserSavedPropertyRow


def list_saved(db: Session) -> list[SavedProperty]:
    model = _model(db)
    query = select(model, ListingRow).join(ListingRow, ListingRow.id == model.listing_id)
    if model is UserSavedPropertyRow:
        query = query.where(model.owner_id == owner_id(db))
    rows = db.execute(query.order_by(model.saved_at.desc(), model.listing_id))
    return [_view(saved, listing) for saved, listing in rows]


def save(db: Session, request: SaveRequest) -> SavedProperty:
    listing = db.get(ListingRow, request.listing_id)
    if listing is None:
        raise NotFound(f"Property {request.listing_id} not found")
    model = _model(db)
    snapshot = None
    if model is UserSavedPropertyRow:
        snapshot = get_property_detail(db, request.listing_id).listing
    key = request.listing_id if model is SavedPropertyRow else (owner_id(db), request.listing_id)
    row = db.get(model, key)
    if row is None:
        row = model(listing_id=request.listing_id)
        if model is UserSavedPropertyRow:
            row.owner_id = owner_id(db)
        db.add(row)
    row.note = request.note.strip() or None if request.note is not None else None
    if snapshot is not None:
        row.data = snapshot.model_dump(mode="json")
    db.commit()
    return _view(row, listing)


def unsave(db: Session, listing_id: str) -> None:
    model = _model(db)
    query = delete(model).where(model.listing_id == listing_id)
    if model is UserSavedPropertyRow:
        query = query.where(model.owner_id == owner_id(db))
    db.execute(query)
    db.commit()


def compare(db: Session, listing_ids: list[str]) -> CompareResult:
    if not 2 <= len(listing_ids) <= 4 or len(set(listing_ids)) != len(listing_ids):
        raise InvalidInput(["query", "ids"], "Select 2-4 distinct properties.")
    return CompareResult(properties=[get_property_detail(db, key) for key in listing_ids])


def _view(row: SavedPropertyRow, listing: ListingRow) -> SavedProperty:
    return SavedProperty(
        listing=Listing.model_validate(
            row.data if isinstance(row, UserSavedPropertyRow) else listing.data
        ),
        note=row.note,
        saved_at=row.saved_at.replace(tzinfo=row.saved_at.tzinfo or UTC),
    )
