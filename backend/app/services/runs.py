"""Pipeline runs and what they found (CHECKLIST I-09, F-02, F-04)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.db.models import (
    AreaIntelRow,
    ListingObservationRow,
    ListingRow,
    ProfileRow,
    RunResultRow,
    RunRow,
)
from app.pipeline.enrichment.area import locality_key
from app.pipeline.orchestrator import to_schema
from app.reference import load_market
from app.schemas.area import AreaIntel
from app.schemas.listing import Listing, ResultKind, Verification
from app.schemas.recommendation import Recommendation
from app.schemas.run import PipelineRun


def get_run(db: Session, run_id: str) -> PipelineRun:
    return to_schema(_get_row(db, run_id))


def get_run_listings(db: Session, run_id: str) -> list[Listing]:
    """Candidates found by this run: priced entries cheapest first, then unpriced projects."""
    _get_row(db, run_id)
    rows = db.scalars(
        select(ListingRow)
        .join(ListingObservationRow, ListingObservationRow.listing_id == ListingRow.id)
        .where(ListingObservationRow.run_id == run_id)
    ).all()
    snapshots = {
        row.listing_id: row.recommendation["listing"]
        for row in db.scalars(select(RunResultRow).where(RunResultRow.run_id == run_id))
        if "listing" in row.recommendation
    }
    listings = [Listing.model_validate(snapshots.get(row.id, row.data)) for row in rows]
    return sorted(
        listings,
        key=lambda item: (
            item.kind is not ResultKind.SNIPPET_ENTRY,
            item.price_inr.value is None,
            item.price_inr.value or 0,
            item.name,
        ),
    )


def get_verifications(db: Session, run_id: str) -> list[Verification]:
    """Completed checks, including rejects; partial results remain readable after a failure."""
    _get_row(db, run_id)
    rows = db.scalars(
        select(RunResultRow).where(RunResultRow.run_id == run_id).order_by(RunResultRow.id)
    )
    return [
        Verification.model_validate(row.recommendation["verification"])
        for row in rows
        if row.recommendation.get("verification") is not None
    ]


def get_recommendations(db: Session, run_id: str) -> list[Recommendation]:
    """Ranked candidates in rank order; empty until the rank stage has run."""
    _get_row(db, run_id)
    rows = db.scalars(
        select(RunResultRow)
        .where(RunResultRow.run_id == run_id, RunResultRow.rank.is_not(None))
        .order_by(RunResultRow.rank)
    )
    return [
        Recommendation(
            rank=row.rank,
            listing=row.recommendation["listing"],
            verification=row.recommendation["verification"],
            **row.recommendation["recommendation"],
        )
        for row in rows
        if row.recommendation.get("recommendation")
    ]


def get_run_areas(db: Session, run_id: str) -> list[AreaIntel]:
    """Area intelligence for the localities of this run's ranked candidates (F-05)."""
    run = _get_row(db, run_id)
    profile = db.get(ProfileRow, run.profile_id)
    city = (profile.data.get("city") if profile else None) or "Bengaluru"
    market = load_market(city)
    slugs = sorted(
        {
            slug
            for row in db.scalars(
                select(RunResultRow).where(
                    RunResultRow.run_id == run_id, RunResultRow.rank.is_not(None)
                )
            )
            if (slug := (row.recommendation["listing"].get("locality") or {}).get("value"))
        }
    )
    areas = []
    for slug in slugs:
        place = market.locality(slug) if market else None
        row = db.get(AreaIntelRow, locality_key(place.name if place else slug, city))
        if row is not None:
            areas.append(AreaIntel.model_validate(row.data))
    return areas


def _get_row(db: Session, run_id: str) -> RunRow:
    row = db.get(RunRow, run_id)
    if row is None:
        raise NotFound(f"Run {run_id} not found")
    return row
