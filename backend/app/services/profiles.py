"""Investor profile CRUD and form options (CHECKLIST F-01).

Profiles are stored as `InvestorProfileIn` JSON in `investor_profiles.data`. Checks that need
reference data (supported city, known localities) live here, not in the schema.
"""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import InvalidInput, NotFound
from app.db.models import (
    AlertRow,
    ListingObservationRow,
    ProfileRow,
    RunAreaRow,
    RunCompetitorRow,
    RunResultRow,
    RunRow,
)
from app.pipeline import targets
from app.reference import load_market
from app.schemas.profile import (
    GOAL_MEASURE,
    MAX_LOCALITIES,
    PROPERTY_TYPE_LABELS,
    SEGMENT_PROPERTY_TYPES,
    InvestmentGoal,
    InvestorProfile,
    InvestorProfileIn,
    RiskAppetite,
    ROIMeasure,
    Segment,
)
from app.schemas.target import TargetSuggestion, TargetSuggestionIn
from app.schemas.views import (
    GoalOption,
    LocalityOption,
    Option,
    ProfileOptions,
    SegmentOption,
)

SEGMENT_LABELS = {Segment.RESIDENTIAL: "Residential", Segment.COMMERCIAL: "Commercial"}
GOAL_LABELS = {
    InvestmentGoal.RENTAL_INCOME: "Rental income",
    InvestmentGoal.APPRECIATION: "Appreciation",
    InvestmentGoal.BALANCED: "Balanced",
}
MEASURE_LABELS = {
    ROIMeasure.RENTAL_YIELD: "Rental yield (annual rent ÷ price, before costs)",
    ROIMeasure.PRICE_GROWTH: "Price growth (locality's past 12 months, or your estimate)",
    ROIMeasure.TOTAL_RETURN: "Total return (rental yield + price growth)",
}
RISK_LABELS = {
    RiskAppetite.CONSERVATIVE: "Conservative",
    RiskAppetite.BALANCED: "Balanced",
    RiskAppetite.AGGRESSIVE: "Aggressive",
}


def profile_options(city: str) -> ProfileOptions:
    market = load_market(city)
    if market is None:
        raise NotFound(f"No reference data for city {city!r}")
    return ProfileOptions(
        city=market.city,
        segments=[
            SegmentOption(
                value=segment,
                label=SEGMENT_LABELS[segment],
                property_types=[
                    Option(value=t, label=PROPERTY_TYPE_LABELS[t])
                    for t in SEGMENT_PROPERTY_TYPES[segment]
                ],
            )
            for segment in Segment
        ],
        localities=[LocalityOption(slug=loc.slug, name=loc.name) for loc in market.localities],
        locality_source=market.locality_source,
        max_localities=MAX_LOCALITIES,
        business_type_suggestions=market.business_type_suggestions,
        goals=[
            GoalOption(
                value=goal,
                label=GOAL_LABELS[goal],
                measure=GOAL_MEASURE[goal],
                measure_label=MEASURE_LABELS[GOAL_MEASURE[goal]],
            )
            for goal in InvestmentGoal
        ],
        risk_levels=[Option(value=level, label=RISK_LABELS[level]) for level in RiskAppetite],
    )


def create_profile(db: Session, data: InvestorProfileIn) -> InvestorProfile:
    _check_reference_data(data)
    row = ProfileRow(data=data.model_dump(mode="json"))
    db.add(row)
    db.commit()
    return _to_schema(row)


def list_profiles(db: Session) -> list[InvestorProfile]:
    rows = db.scalars(select(ProfileRow).order_by(ProfileRow.updated_at.desc())).all()
    return [_to_schema(row) for row in rows]


def get_profile(db: Session, profile_id: str) -> InvestorProfile:
    return _to_schema(_get_row(db, profile_id))


def update_profile(db: Session, profile_id: str, data: InvestorProfileIn) -> InvestorProfile:
    row = _get_row(db, profile_id)
    _check_reference_data(data)
    row.data = data.model_dump(mode="json")
    db.commit()
    return _to_schema(row)


def delete_profile(db: Session, profile_id: str) -> None:
    """Delete the profile with its runs, their observations and its alerts. Discovered listings
    stay: other runs may share them. The search ledger keeps its rows for budget history."""
    row = _get_row(db, profile_id)
    run_ids = select(RunRow.id).where(RunRow.profile_id == profile_id)
    db.execute(delete(ListingObservationRow).where(ListingObservationRow.run_id.in_(run_ids)))
    db.execute(delete(RunResultRow).where(RunResultRow.run_id.in_(run_ids)))
    db.execute(delete(RunAreaRow).where(RunAreaRow.run_id.in_(run_ids)))
    db.execute(delete(RunCompetitorRow).where(RunCompetitorRow.run_id.in_(run_ids)))
    db.execute(delete(RunRow).where(RunRow.profile_id == profile_id))
    db.execute(delete(AlertRow).where(AlertRow.profile_id == profile_id))
    db.delete(row)
    db.commit()


def _get_row(db: Session, profile_id: str) -> ProfileRow:
    row = db.get(ProfileRow, profile_id)
    if row is None:
        raise NotFound(f"Profile {profile_id} not found")
    return row


def _check_reference_data(data: InvestorProfileIn) -> None:
    market = load_market(data.city)
    if market is None:
        raise InvalidInput(["body", "city"], f"{data.city} is not a supported city")
    unknown = [slug for slug in data.localities if market.locality(slug) is None]
    if unknown:
        raise InvalidInput(
            ["body", "localities"], f"unknown localities for {market.city}: {', '.join(unknown)}"
        )


def _to_schema(row: ProfileRow) -> InvestorProfile:
    return InvestorProfile(
        id=row.id,
        created_at=_as_utc(row.created_at),
        updated_at=_as_utc(row.updated_at),
        **row.data,
    )


def _as_utc(value: datetime) -> datetime:
    # SQLite drops the timezone on the way back in; every timestamp we write is UTC.
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def suggest_target(db: Session, data: TargetSuggestionIn) -> TargetSuggestion:
    """A sourced, typical target ROI for the profile being written (ADR 0018)."""
    market = load_market(data.city)
    if market is None:
        raise InvalidInput(["body", "city"], f"{data.city} is not a supported city")
    unknown = [slug for slug in data.localities if market.locality(slug) is None]
    if unknown:
        raise InvalidInput(
            ["body", "localities"], f"unknown localities for {market.city}: {', '.join(unknown)}"
        )
    return targets.suggest_target(db, get_settings(), market, data)
