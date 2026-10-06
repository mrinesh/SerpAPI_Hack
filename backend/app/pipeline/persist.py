"""Save discovered candidates: upsert `listings`, record one observation per run."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ListingObservationRow, ListingRow, RunResultRow
from app.schemas.listing import Listing, Verification
from app.schemas.recommendation import Recommendation


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
        snapshot = db.scalar(
            select(RunResultRow).where(
                RunResultRow.run_id == run_id, RunResultRow.listing_id == listing.id
            )
        )
        if snapshot is None:
            db.add(
                RunResultRow(
                    run_id=run_id,
                    listing_id=listing.id,
                    rank=None,
                    recommendation={
                        "listing": listing.model_dump(mode="json"),
                        "verification": None,
                    },
                )
            )
    db.commit()


def save_verification(
    db: Session, run_id: str, listing: Listing, verification: Verification
) -> None:
    """Commit each result independently so earlier checks survive a later provider failure."""
    save_candidates(db, run_id, [listing])
    observation = db.scalar(
        select(ListingObservationRow).where(
            ListingObservationRow.run_id == run_id, ListingObservationRow.listing_id == listing.id
        )
    )
    observation.price_inr = listing.price_inr.value
    result = db.scalar(
        select(RunResultRow).where(
            RunResultRow.run_id == run_id, RunResultRow.listing_id == listing.id
        )
    )
    result.rank = None  # Ranking belongs to F-04; rejects are always retained.
    result.recommendation = {
        "listing": listing.model_dump(mode="json"),
        "verification": verification.model_dump(mode="json"),
    }
    db.commit()


def save_recommendation(db: Session, run_id: str, recommendation: Recommendation) -> None:
    """Set the rank and add the ranking fields to the run's snapshot; one commit each, so code
    reasons survive a later explanation failure."""
    result = db.scalar(
        select(RunResultRow).where(
            RunResultRow.run_id == run_id,
            RunResultRow.listing_id == recommendation.listing.id,
        )
    )
    result.rank = recommendation.rank
    result.recommendation = {
        **result.recommendation,
        "recommendation": recommendation.model_dump(
            mode="json",
            include={
                "score",
                "score_breakdown",
                "reason",
                "highlights",
                "risks",
                "explained",
                "access",
            },
        ),
    }
    db.commit()
