"""Save discovered candidates: upsert `listings`, record one observation per run."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ListingObservationRow, ListingRow
from app.schemas.listing import Listing


def save_candidates(db: Session, run_id: str, listings: list[Listing]) -> None:
    now = datetime.now(UTC)
    unique = {listing.id: listing for listing in listings}
    for listing in unique.values():
        row = db.get(ListingRow, listing.id)
        if row is None:
            row = ListingRow(id=listing.id, first_seen_at=now)
            db.add(row)
        else:
            first_seen = row.first_seen_at
            listing.first_seen_at = first_seen.replace(tzinfo=first_seen.tzinfo or UTC)
        listing.last_seen_at = now
        row.kind = listing.kind
        row.portal = listing.portal
        row.locality = listing.locality.value
        row.price_inr = listing.price_inr.value
        row.size_sqft = listing.size_sqft.value
        row.price_per_sqft = listing.price_per_sqft.value
        row.last_seen_at = now
        row.data = listing.model_dump(mode="json")
    # Observations reference listings; without ORM relationships the flush order is not
    # guaranteed, so the listing rows go in first.
    db.flush()
    seen = set(
        db.scalars(
            select(ListingObservationRow.listing_id).where(ListingObservationRow.run_id == run_id)
        )
    )
    for listing in unique.values():
        if listing.id not in seen:
            db.add(
                ListingObservationRow(
                    listing_id=listing.id, run_id=run_id, price_inr=listing.price_inr.value
                )
            )
    db.commit()
