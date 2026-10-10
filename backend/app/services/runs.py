"""Pipeline runs and what they found (CHECKLIST I-09, F-02, F-04)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.db.models import (
    AreaIntelRow,
    ListingObservationRow,
    ListingRow,
    ProfileRow,
    RunAreaRow,
    RunCompetitorRow,
    RunDevelopmentRow,
    RunResultRow,
    RunRow,
)
from app.pipeline.enrichment.area import locality_key
from app.pipeline.orchestrator import to_schema
from app.reference import load_market
from app.schemas.area import AreaIntel
from app.schemas.competitor import CompetitorReport
from app.schemas.development import AreaDevelopment
from app.schemas.listing import Listing, ResultKind, Verification
from app.schemas.recommendation import Recommendation
from app.schemas.run import PipelineRun
from app.services.forecast import project_interest


def get_run(db: Session, run_id: str) -> PipelineRun:
    return to_schema(get_run_row(db, run_id))


def get_run_listings(db: Session, run_id: str) -> list[Listing]:
    """Candidates found by this run: priced entries cheapest first, then unpriced projects."""
    get_run_row(db, run_id)
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
    get_run_row(db, run_id)
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
    get_run_row(db, run_id)
    rows = db.scalars(
        select(RunResultRow)
        .where(RunResultRow.run_id == run_id, RunResultRow.rank.is_not(None))
        .order_by(RunResultRow.rank)
    )
    return [rec for row in rows if (rec := recommendation_from_row(row)) is not None]


def recommendation_from_row(row: RunResultRow) -> Recommendation | None:
    """The ranked recommendation stored on a run result, or None when it was not ranked."""
    if row.rank is None or not row.recommendation.get("recommendation"):
        return None
    return Recommendation(
        rank=row.rank,
        listing=row.recommendation["listing"],
        verification=row.recommendation["verification"],
        **row.recommendation["recommendation"],
    )


def get_run_areas(db: Session, run_id: str) -> list[AreaIntel]:
    """The area evidence this run used, frozen at enrichment (ADR 0020). Runs from before
    snapshots existed fall back to the shared locality cache."""
    run = get_run_row(db, run_id)
    frozen = db.scalars(
        select(RunAreaRow).where(RunAreaRow.run_id == run_id).order_by(RunAreaRow.locality_key)
    ).all()
    if frozen:
        return [AreaIntel.model_validate(row.data) for row in frozen]
    city = run_city(db, run)
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
    return [area for slug in slugs if (area := _cached_area(db, slug, city)) is not None]


def area_for_run(db: Session, run: RunRow, slug: str) -> AreaIntel | None:
    """The area one run used for one locality: its frozen snapshot, else the shared cache."""
    city = run_city(db, run)
    key = _area_key(slug, city)
    frozen = db.scalar(
        select(RunAreaRow).where(RunAreaRow.run_id == run.id, RunAreaRow.locality_key == key)
    )
    if frozen is not None:
        return AreaIntel.model_validate(frozen.data)
    return _cached_area(db, slug, city)


def get_run_competitors(db: Session, run_id: str) -> list[CompetitorReport]:
    """Same-category businesses around each commercial locality, as this run saw them (F-06).
    Empty for residential runs and runs from before F-06."""
    get_run_row(db, run_id)
    rows = db.scalars(
        select(RunCompetitorRow)
        .where(RunCompetitorRow.run_id == run_id)
        .order_by(RunCompetitorRow.locality_key)
    )
    return [CompetitorReport.model_validate(row.data) for row in rows]


def get_run_development(db: Session, run_id: str) -> list[AreaDevelopment]:
    """Developing-area reports this run froze (ADR 0025): research priorities first, then the
    rest by locality. Empty until enrichment, and for runs from before the feature."""
    get_run_row(db, run_id)
    rows = db.scalars(select(RunDevelopmentRow).where(RunDevelopmentRow.run_id == run_id))
    reports = [AreaDevelopment.model_validate(row.data) for row in rows]
    for report in reports:
        report.forecasts = [
            project_interest(signal, report.as_of.date()) for signal in report.public_interest
        ]
    return sorted(reports, key=lambda r: (r.rank is None, r.rank or 0, r.locality_key))


def competitors_for_run(db: Session, run: RunRow, slug: str) -> CompetitorReport | None:
    """The competitor report one run froze for one locality, if any."""
    key = _area_key(slug, run_city(db, run))
    row = db.scalar(
        select(RunCompetitorRow).where(
            RunCompetitorRow.run_id == run.id, RunCompetitorRow.locality_key == key
        )
    )
    return CompetitorReport.model_validate(row.data) if row is not None else None


def run_city(db: Session, run: RunRow) -> str:
    profile = db.get(ProfileRow, run.profile_id)
    return (profile.data.get("city") if profile else None) or "Bengaluru"


def _area_key(slug: str, city: str) -> str:
    market = load_market(city)
    place = market.locality(slug) if market else None
    return locality_key(place.name if place else slug, city)


def _cached_area(db: Session, slug: str, city: str) -> AreaIntel | None:
    row = db.get(AreaIntelRow, _area_key(slug, city))
    return AreaIntel.model_validate(row.data) if row is not None else None


def get_run_row(db: Session, run_id: str) -> RunRow:
    row = db.get(RunRow, run_id)
    if row is None:
        raise NotFound(f"Run {run_id} not found")
    return row
