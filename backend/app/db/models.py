"""Database tables (CHECKLIST I-08). docs/DATA_MODEL.md explains each table.

Nested domain objects (listings, area intel, recommendations) are stored as JSON produced by
their Pydantic schema in app/schemas, so the schema module stays the single source of truth for
their shape. Columns exist only for what we filter, join or sort on.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_id, utcnow


class ProfileRow(Base):
    __tablename__ = "investor_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)  # schemas.profile.InvestorProfileIn
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class RunRow(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    profile_id: Mapped[str] = mapped_column(ForeignKey("investor_profiles.id"), index=True)
    status: Mapped[str] = mapped_column(String(16))  # schemas.run.RunStatus
    current_stage: Mapped[str | None] = mapped_column(String(16))
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # StageEvent[]
    searches_used: Mapped[int] = mapped_column(Integer, default=0)
    cache_hits: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ListingRow(Base):
    """One row per discovered candidate, shared across runs (enables price-drop alerts).

    `id` is a stable hash of the candidate's identity (pipeline/cleaning.py), so the same
    snippet entry or Maps project maps to the same row in every run (ADR 0011).
    """

    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # schemas.listing.ResultKind
    portal: Mapped[str] = mapped_column(String(32))
    locality: Mapped[str | None] = mapped_column(String(64), index=True)  # locality slug
    price_inr: Mapped[int | None] = mapped_column(Integer)
    size_sqft: Mapped[float | None] = mapped_column(Float)
    price_per_sqft: Mapped[float | None] = mapped_column(Float)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)  # schemas.listing.Listing
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ListingObservationRow(Base):
    """A candidate seen in a run, at a price: both "found in this run" and price history."""

    __tablename__ = "listing_observations"
    __table_args__ = (UniqueConstraint("listing_id", "run_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id"), index=True)
    price_inr: Mapped[int | None] = mapped_column(Integer)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RunResultRow(Base):
    """A listing's verification, metrics and rank within one run."""

    __tablename__ = "run_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id"), index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    rank: Mapped[int | None] = mapped_column(Integer)  # null until ranked, or when rejected
    # Progressive payload: listing snapshot + optional Verification; F-04 adds recommendation.
    recommendation: Mapped[dict[str, Any]] = mapped_column(JSON)


class RunAreaRow(Base):
    """The area evidence one run used, frozen: later cache refreshes do not change it (ADR 0020,
    after gscode007's F-05 branch; the per-run snapshot rule of ADR 0013)."""

    __tablename__ = "run_area_intel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.id"), index=True)
    locality_key: Mapped[str] = mapped_column(String(128))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)  # schemas.area.AreaIntel


class AreaIntelRow(Base):
    __tablename__ = "area_intel"

    locality_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)  # schemas.area.AreaIntel
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CompetitorReportRow(Base):
    __tablename__ = "competitor_reports"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)  # hash(center, category, radius)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)  # schemas.competitor.CompetitorReport
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SerpCacheRow(Base):
    """Raw SerpApi responses keyed by `integrations.serpapi.gateway.cache_key`."""

    __tablename__ = "serp_cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    engine: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
    search_id: Mapped[str | None] = mapped_column(String(64))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchLedgerRow(Base):
    """One row per SerpApi lookup, live or cached. The search budget is computed from this."""

    __tablename__ = "search_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), index=True)
    engine: Mapped[str] = mapped_column(String(32))
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    live: Mapped[bool] = mapped_column(Boolean)  # False = served from cache or fixture
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LlmCacheRow(Base):
    __tablename__ = "llm_cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)  # hash(task, model, prompt)
    task: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SavedPropertyRow(Base):
    __tablename__ = "saved_properties"

    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), primary_key=True)
    note: Mapped[str | None] = mapped_column(Text)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AlertRow(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    profile_id: Mapped[str] = mapped_column(ForeignKey("investor_profiles.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # schemas.views.AlertKind
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
