"""Pipeline runs and what they found (CHECKLIST I-09, F-02, F-04)."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFound, NotImplementedYet
from app.db.models import ListingObservationRow, ListingRow, RunAreaIntelRow, RunResultRow, RunRow
from app.pipeline.enrichment.area import as_utc
from app.pipeline.orchestrator import to_schema
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
    raise NotImplementedYet("F-04", "Reading ranked recommendations")


def get_areas(db: Session, run_id: str) -> list[AreaIntel]:
    """Frozen run snapshots, including partial results and that run's existing price levels."""
    _get_row(db, run_id)
    rows = db.scalars(
        select(RunAreaIntelRow)
        .where(RunAreaIntelRow.run_id == run_id)
        .order_by(RunAreaIntelRow.locality_key)
    )
    areas = [AreaIntel.model_validate(row.data) for row in rows]
    return [
        area.model_copy(update={"stale": as_utc(area.expires_at) <= datetime.now(UTC)})
        for area in areas
    ]


def _get_row(db: Session, run_id: str) -> RunRow:
    row = db.get(RunRow, run_id)
    if row is None:
        raise NotFound(f"Run {run_id} not found")
    return row
