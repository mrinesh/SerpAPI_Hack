"""Single-property and single-locality views (CHECKLIST F-07, F-05)."""

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFound
from app.db.models import AreaIntelRow, ListingObservationRow, ListingRow, RunResultRow, RunRow
from app.schemas.area import AreaIntel
from app.schemas.competitor import CompetitorReport
from app.schemas.listing import Listing, Verification
from app.schemas.metrics import InvestmentMetrics
from app.schemas.provenance import Sourced, SourceRef
from app.schemas.views import PriceObservation, PropertyDetail
from app.services.runs import (
    area_for_run,
    competitors_for_run,
    get_run_row,
    recommendation_from_row,
)


def get_property_detail(db: Session, listing_id: str, run_id: str | None = None) -> PropertyDetail:
    """One listing as one run judged it; without `run_id`, the latest run that saw it (ADR 0021).
    Assembled from stored results only: no searches, no LLM calls."""
    listing_row = db.get(ListingRow, listing_id)
    if listing_row is None:
        raise NotFound(f"Property {listing_id} not found")
    query = select(RunResultRow).where(RunResultRow.listing_id == listing_id)
    if run_id is not None:
        get_run_row(db, run_id)
        query = query.where(RunResultRow.run_id == run_id)
    else:
        query = query.join(RunRow, RunRow.id == RunResultRow.run_id).order_by(
            RunRow.created_at.desc(), RunResultRow.id.desc()
        )
    result = db.scalars(query.limit(1)).first()
    if result is None:
        raise NotFound(
            f"Property {listing_id} was not found by run {run_id}"
            if run_id
            else f"Property {listing_id} has no run results"
        )
    run = get_run_row(db, result.run_id)
    listing = Listing.model_validate(result.recommendation.get("listing") or listing_row.data)
    stored_check = result.recommendation.get("verification")
    verification = Verification.model_validate(stored_check) if stored_check else None
    recommendation = recommendation_from_row(result)
    metrics = recommendation.metrics if recommendation else None
    slug = listing.locality.value
    area = area_for_run(db, run, slug) if slug else None
    competitors = competitors_for_run(db, run, slug) if slug else None
    return PropertyDetail(
        run_id=run.id,
        profile_id=run.profile_id,
        listing=listing,
        verification=verification,
        recommendation=recommendation,
        metrics=metrics,
        area=area,
        competitors=competitors,
        price_history=_price_history(db, listing_id),
        sources=collect_sources(listing, metrics, area, competitors),
    )


def collect_sources(
    listing: Listing,
    metrics: InvestmentMetrics | None,
    area: AreaIntel | None,
    competitors: CompetitorReport | None = None,
) -> list[SourceRef]:
    """Every source behind the listing's facts, its metrics, the area figures it uses and the
    nearby businesses counted (F-06), in that order and de-duplicated. News is display only and
    feeds no figure, so it is left out."""
    refs: list[SourceRef] = [*listing.sources, *_sourced_refs(listing)]
    if metrics is not None:
        refs += _sourced_refs(metrics)
    if area is not None:
        kind = listing.property_type.value
        for value in (
            area.price_levels.get(kind) if kind else None,
            area.rent_levels.get(kind) if kind else None,
            area.price_growth_pct,
        ):
            if value is not None:
                refs += value.sources
        refs += [amenity.source for amenity in area.amenities]
    if competitors is not None:
        refs += [place.source for place in competitors.competitors]
    unique: dict[tuple, SourceRef] = {}
    for ref in refs:
        if ref.url or ref.search_id:
            unique.setdefault((ref.engine, ref.url, ref.search_id), ref)
    return list(unique.values())


def _sourced_refs(model: BaseModel) -> list[SourceRef]:
    return [
        ref
        for name in type(model).model_fields
        if isinstance(value := getattr(model, name), Sourced)
        for ref in value.sources
    ]


def _price_history(db: Session, listing_id: str) -> list[PriceObservation]:
    rows = db.scalars(
        select(ListingObservationRow)
        .where(ListingObservationRow.listing_id == listing_id)
        .order_by(ListingObservationRow.seen_at, ListingObservationRow.id)
    )
    return [
        PriceObservation(run_id=row.run_id, price_inr=row.price_inr, seen_at=row.seen_at)
        for row in rows
    ]


def get_area(db: Session, locality_key: str) -> AreaIntel:
    """The cached area for a key like `bengaluru/whitefield`, even if past its refresh time."""
    row = db.get(AreaIntelRow, locality_key)
    if row is None:
        raise NotFound(f"No area intelligence for {locality_key}")
    try:
        return AreaIntel.model_validate(row.data)
    except ValidationError as exc:
        # Never trust or silently repair a corrupt row on a read; the next run rebuilds it.
        raise AppError(
            f"The cached area for {locality_key} is unreadable; run a search to rebuild it.",
            details={"locality_key": locality_key, "operation": "area_cache_read"},
        ) from exc
