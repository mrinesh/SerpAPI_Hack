"""Runs the pipeline end to end (CHECKLIST I-09). docs/PIPELINE.md has the stage-by-stage detail.

    plan -> fetch -> clean -> verify -> enrich -> rank

`start_run` creates a `pipeline_runs` row and runs `run_pipeline` on a background thread with its
own database session; the UI polls `GET /api/runs/{id}` for `StageEvent`s. Built so far: plan,
fetch and clean (F-02), and verify (F-03). Later stages are reported as not built yet.
A failing stage marks the
run failed but keeps everything saved so far.
"""

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import AppError, InvalidInput
from app.db.models import RunRow, SearchLedgerRow
from app.db.session import SessionLocal
from app.integrations.llm.factory import get_llm
from app.integrations.serpapi.gateway import SerpApiGateway
from app.pipeline.cleaning import normalize_hits
from app.pipeline.context import PipelineContext
from app.pipeline.discovery import fetch_hits
from app.pipeline.enrichment.area import get_area_intel
from app.pipeline.enrichment.price_level import price_levels
from app.pipeline.metrics import compute_metrics
from app.pipeline.persist import save_candidates, save_recommendation, save_verification
from app.pipeline.query_planner import plan_queries
from app.pipeline.ranking import EXPLAIN_TOP, explain, level_for, place_name, score_candidates
from app.pipeline.verification import extract, verify
from app.reference import load_market
from app.schemas.run import PipelineRun, PipelineStage, RunStatus, StageEvent
from app.services import profiles

log = logging.getLogger(__name__)

STAGE_ORDER: tuple[PipelineStage, ...] = (
    PipelineStage.PLAN,
    PipelineStage.FETCH,
    PipelineStage.CLEAN,
    PipelineStage.VERIFY,
    PipelineStage.ENRICH,
    PipelineStage.RANK,
)


class StageFailed(Exception):
    """A stage could not produce anything usable; the message is shown to the investor."""


def start_run(db: Session, profile_id: str) -> PipelineRun:
    """Create the run record and run the pipeline in the background."""
    profiles.get_profile(db, profile_id)  # 404 for an unknown profile
    run = RunRow(
        profile_id=profile_id,
        status=RunStatus.PENDING,
        events=[
            StageEvent(stage=s, status=RunStatus.PENDING).model_dump(mode="json")
            for s in STAGE_ORDER
        ],
    )
    db.add(run)
    db.commit()
    _launch(run.id)
    return to_schema(run)


def _launch(run_id: str) -> None:
    """Start the run on a daemon thread. Tests replace this to run inline."""
    threading.Thread(
        target=run_pipeline, args=(run_id,), name=f"run-{run_id[:8]}", daemon=True
    ).start()


def run_pipeline(run_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        run = db.get(RunRow, run_id)
        tracker = _Tracker(db, run)
        tracker.set_status(RunStatus.RUNNING)
        try:
            profile = profiles.get_profile(db, run.profile_id)
            market = load_market(profile.city)
            if market is None:
                raise InvalidInput(["city"], f"{profile.city} is not a supported city")
            ctx = PipelineContext(
                run_id=run_id,
                profile=profile,
                settings=settings,
                db=db,
                serp=SerpApiGateway(settings, db),
                llm=get_llm(settings, db),
                emit=tracker.replace,
            )

            with tracker.stage(PipelineStage.PLAN) as event:
                queries = plan_queries(profile, settings, market)
                google = sum(1 for q in queries if q.retry_params is not None)
                event.counts = {"queries": len(queries)}
                event.message = (
                    f"{google} Google and {len(queries) - google} Google Maps searches planned"
                )

            with tracker.stage(PipelineStage.FETCH) as event:
                hits, report = fetch_hits(ctx, queries)
                tracker.update_search_counts()
                pages = sum(1 for h in hits if h.place_type is None)
                event.counts = {
                    "searches": report.searches,
                    "live": report.live,
                    "retries": report.retries,
                    "pages": pages,
                    "places": len(hits) - pages,
                }
                notes = [f"{report.live} of {report.searches} searches spent a credit"]
                if report.empty:
                    notes.append("no usable results for: " + "; ".join(report.empty))
                notes.extend(report.errors)
                event.message = ". ".join(notes)
                if not hits and report.errors:
                    raise StageFailed(report.errors[0])

            with tracker.stage(PipelineStage.CLEAN) as event:
                result = normalize_hits(
                    hits, segment=profile.segment, market=market, now=datetime.now(UTC)
                )
                save_candidates(db, run_id, result.listings)
                event.counts = {
                    "candidates": len(result.listings),
                    "entries": result.entries,
                    "projects": result.projects,
                    "matched": result.matched_projects,
                    "merged": result.merged_duplicates,
                }
                event.message = (
                    f"{len(result.listings)} candidates from {result.pages} portal pages "
                    f"and {result.projects} Google Maps projects"
                )

            with tracker.stage(PipelineStage.VERIFY) as event:
                # Discovery order is deterministic, so a capped run checks the same candidates.
                checking = result.listings[: settings.verify_max_candidates]
                event.counts = {
                    "candidates": len(result.listings),
                    "checked": 0,
                    "rejected": 0,
                    "flagged": 0,
                    "unchecked": len(result.listings) - len(checking),
                }
                event.message = "Looking up locality price levels"
                tracker.replace(event)
                # Benchmarks for price flags: one search per locality and type (ADR 0014).
                levels, level_notes = price_levels(ctx, market, result.listings)
                checked = []
                for listing in checking:
                    extracted = extract(ctx, listing)
                    benchmark = levels.get(
                        (extracted.locality.value, extracted.property_type.value)
                    )
                    verification = verify(ctx, extracted, benchmark)
                    save_verification(db, run_id, extracted, verification)
                    checked.append((extracted, verification))
                    event.counts["checked"] += 1
                    event.counts["rejected"] += int(verification.verdict == "reject")
                    event.counts["flagged"] += int(
                        any(flag.kind == "too_good_to_be_true" for flag in verification.flags)
                    )
                    event.message = (
                        f"Checked {event.counts['checked']} of {len(checking)} candidates; "
                        f"{event.counts['rejected']} filtered out, "
                        f"{event.counts['flagged']} flagged as implausibly cheap"
                    )
                    tracker.replace(event)
                if level_notes and checking:
                    event.message += ". Price levels: " + "; ".join(level_notes)
                if event.counts["unchecked"]:
                    event.message += (
                        f"; {event.counts['unchecked']} more not checked "
                        f"(limit {settings.verify_max_candidates} per run)"
                    )
                if not result.listings:
                    event.message = "No candidates to verify"

            with tracker.stage(PipelineStage.ENRICH) as event:
                # One shared, cached area per locality of the rankable candidates (ADR 0006).
                localities = sorted(
                    {
                        listing.locality.value
                        for listing, verification in checked
                        if verification.verdict != "reject" and listing.locality.value
                    }
                )
                areas = {}
                notes = []
                event.counts = {"localities": len(localities), "from_cache": 0, "area_warnings": 0}
                for slug in localities:
                    local_levels = {t: lvl for (loc, t), lvl in levels.items() if loc == slug}
                    area, cached = get_area_intel(
                        ctx, market, slug, local_levels, set(ctx.profile.property_types)
                    )
                    areas[slug] = area
                    event.counts["from_cache"] += int(cached)
                    event.counts["area_warnings"] += len(area.warnings)
                    notes.append(_area_note(area, cached))
                    event.message = "; ".join(notes)
                    tracker.replace(event)
                # Investment metrics per rankable candidate (F-09, ADR 0010 / 0017).
                metrics = {}
                for listing, verification in checked:
                    if verification.verdict == "reject":
                        continue
                    area = areas.get(listing.locality.value or "")
                    kind = listing.property_type.value
                    metrics[listing.id] = compute_metrics(
                        listing,
                        verification,
                        ctx.profile,
                        price_level=levels.get((listing.locality.value, kind)),
                        rent_level=area.rent_levels.get(kind) if area and kind else None,
                        area_growth=area.price_growth_pct if area else None,
                    )
                event.counts["with_yield"] = sum(
                    m.rental_yield_pct.value is not None for m in metrics.values()
                )
                if not localities:
                    event.message = "No localities to enrich"

            with tracker.stage(PipelineStage.RANK) as event:
                # Scores and code reasons are saved first, so an explanation failure keeps them.
                ranked = score_candidates(ctx.profile, checked, levels, market, areas, metrics)
                for recommendation in ranked:
                    save_recommendation(db, run_id, recommendation)
                top = ranked[:EXPLAIN_TOP]
                event.counts = {"ranked": len(ranked), "explained": 0}
                event.message = (
                    f"Ranked {len(ranked)} candidates; writing reasons for the top {len(top)}"
                )
                tracker.replace(event)
                for recommendation in top:
                    written = explain(
                        ctx,
                        recommendation,
                        len(ranked),
                        level_for(levels, recommendation.listing),
                        place_name(market, recommendation.listing),
                        _growth(areas, recommendation.listing),
                    )
                    save_recommendation(db, run_id, written)
                    event.counts["explained"] += int(written.explained)
                event.message = (
                    f"Ranked {len(ranked)} candidates; "
                    f"{event.counts['explained']} of the top {len(top)} explained by AI"
                    if ranked
                    else "No candidates to rank"
                )
            tracker.finish(RunStatus.SUCCEEDED)
        except Exception as exc:  # the run must end in a recorded state, whatever happened
            if not isinstance(exc, (AppError, StageFailed)):
                log.exception("Run %s failed", run_id)
            tracker.finish(RunStatus.FAILED, _message(exc))


def to_schema(run: RunRow) -> PipelineRun:
    return PipelineRun(
        id=run.id,
        profile_id=run.profile_id,
        status=run.status,
        current_stage=run.current_stage,
        events=[StageEvent.model_validate(e) for e in run.events],
        searches_used=run.searches_used,
        cache_hits=run.cache_hits,
        error=run.error,
        created_at=_utc(run.created_at),
        finished_at=_utc(run.finished_at) if run.finished_at else None,
    )


class _Tracker:
    """Keeps the run row and its stage events current, committing after every change."""

    def __init__(self, db: Session, run: RunRow) -> None:
        self._db = db
        self._run = run

    def set_status(self, status: RunStatus) -> None:
        self._run.status = status
        self._db.commit()

    @contextmanager
    def stage(self, stage: PipelineStage) -> Iterator[StageEvent]:
        event = StageEvent(stage=stage, status=RunStatus.RUNNING, started_at=datetime.now(UTC))
        self._run.current_stage = stage
        self.replace(event)
        try:
            yield event
        except Exception as exc:
            self._db.rollback()  # the session may be mid-transaction after a failed write
            event.status = RunStatus.FAILED
            event.message = _message(exc)
            event.finished_at = datetime.now(UTC)
            self.replace(event)
            raise
        event.status = RunStatus.SUCCEEDED
        event.finished_at = datetime.now(UTC)
        self.replace(event)

    def note(self, stage: PipelineStage, message: str) -> None:
        self.replace(StageEvent(stage=stage, status=RunStatus.PENDING, message=message))

    def replace(self, event: StageEvent) -> None:
        events = [e for e in self._run.events if e["stage"] != event.stage]
        events.append(event.model_dump(mode="json"))
        order = {s.value: i for i, s in enumerate(STAGE_ORDER)}
        self._run.events = sorted(events, key=lambda e: order[e["stage"]])  # new list: tracked
        self._db.commit()

    def update_search_counts(self) -> None:
        def count(live: bool) -> int:
            return (
                self._db.scalar(
                    select(func.count())
                    .select_from(SearchLedgerRow)
                    .where(SearchLedgerRow.run_id == self._run.id, SearchLedgerRow.live == live)
                )
                or 0
            )

        self._run.searches_used = count(True)
        self._run.cache_hits = count(False)
        self._db.commit()

    def finish(self, status: RunStatus, error: str | None = None) -> None:
        self._db.rollback()  # drop anything half-written by a failed stage
        self._run.status = status
        self._run.error = error
        self._run.finished_at = datetime.now(UTC)
        self._db.commit()


def _message(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    if isinstance(exc, StageFailed):
        return str(exc)
    return f"Unexpected error ({type(exc).__name__}); see the backend log."


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _area_note(area, cached: bool) -> str:
    metro = next((a for a in area.amenities if a.category == "metro"), None)
    parts = [f"metro {metro.distance_km:.1f} km" if metro else "no metro found"]
    if area.price_growth_pct is not None:
        parts.append(f"growth {area.price_growth_pct.value:g}% (past 12 months)")
    for kind, rent in sorted(area.rent_levels.items()):
        parts.append(f"{kind} rent ₹{rent.value:g}/sq ft/month")
    if area.warnings:
        failed = ", ".join(f"{w.section} ({w.code})" for w in area.warnings)
        parts.append(f"{len(area.warnings)} section(s) could not be loaded: {failed}")
    return f"{area.locality}: {', '.join(parts)}" + (" (cached)" if cached else "")


def _growth(areas: dict, listing):
    area = areas.get(listing.locality.value or "")
    return area.price_growth_pct if area else None
