"""Runs the pipeline end to end (CHECKLIST I-09). docs/PIPELINE.md has the stage-by-stage detail.

    plan -> fetch -> clean -> verify -> enrich -> rank

`start_run` creates a `pipeline_runs` row and runs `run_pipeline` on a background thread with its
own database session; the UI polls `GET /api/runs/{id}` for `StageEvent`s. Built so far: plan,
fetch and clean (F-02), verify (F-03), area enrichment (F-05) and investment metrics (F-09).
Ranking is not built yet.
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
from app.db.models import RunAreaIntelRow, RunRow, SearchLedgerRow
from app.db.session import SessionLocal
from app.integrations.llm.factory import get_llm
from app.integrations.serpapi.gateway import SerpApiGateway
from app.pipeline.cleaning import normalize_hits
from app.pipeline.context import PipelineContext
from app.pipeline.discovery import fetch_hits
from app.pipeline.enrichment.area import get_area_intel
from app.pipeline.enrichment.investment import InvestmentInputs
from app.pipeline.enrichment.price_level import price_levels
from app.pipeline.metrics import compute_metrics
from app.pipeline.persist import save_candidates, save_metrics, save_verification
from app.pipeline.query_planner import plan_queries
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
NOT_BUILT = {
    PipelineStage.RANK: "F-04",
}


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
                extracted_by_id = {}
                checks_by_id = {}
                for listing in checking:
                    extracted = extract(ctx, listing)
                    benchmark = levels.get(
                        (extracted.locality.value, extracted.property_type.value)
                    )
                    verification = verify(ctx, extracted, benchmark)
                    save_verification(db, run_id, extracted, verification)
                    extracted_by_id[listing.id] = extracted
                    checks_by_id[listing.id] = verification
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
                candidates = [extracted_by_id.get(item.id, item) for item in result.listings]
                inputs = InvestmentInputs(ctx, market)
                areas = {}
                localities = sorted(
                    {
                        listing.locality.value
                        for listing in result.listings
                        if listing.locality.value
                    }
                )
                event.counts = {
                    "localities": len(localities),
                    "areas": 0,
                    "warnings": 0,
                    "cache_hits": 0,
                    "metrics": 0,
                    "roi_assessed": 0,
                    "investment_warnings": 0,
                }
                for locality in localities:
                    event.message = f"Enriching {locality}"
                    tracker.replace(event)
                    area = get_area_intel(
                        ctx,
                        locality,
                        benchmarks={
                            kind: value
                            for (slug, kind), value in levels.items()
                            if slug == locality
                        },
                    )
                    areas[locality] = area
                    db.merge(
                        RunAreaIntelRow(
                            run_id=run_id,
                            locality_key=area.locality_key,
                            data=area.model_dump(mode="json"),
                        )
                    )
                    db.commit()
                    event.counts["areas"] += 1
                    event.counts["warnings"] += len(area.warnings)
                    event.counts["cache_hits"] += int(area.cache_hit)
                    tracker.update_search_counts()
                    event.message = (
                        f"{event.counts['areas']} of {len(localities)} localities enriched; "
                        f"{event.counts['warnings']} section warnings. "
                        "Computing investment metrics next."
                    )
                    tracker.replace(event)
                if not localities:
                    event.message = "No discovered localities to enrich"
                for listing in candidates:
                    check = checks_by_id.get(listing.id)
                    blocked = None
                    if check is None:
                        blocked = "Candidate has not completed relevance/price verification."
                    elif check.verdict == "reject":
                        blocked = "Candidate fails the profile criteria; ROI assessment withheld."
                    elif any(flag.kind == "too_good_to_be_true" for flag in check.flags):
                        blocked = (
                            "Implausibly cheap quote: confirm the sale price before assessing ROI."
                        )
                    if listing.price_inr.note and any(
                        word in listing.price_inr.note.lower()
                        for word in ("range", "starting price", "lower bound")
                    ):
                        blocked = (
                            blocked or "Final unit price is unconfirmed (range or starting price)."
                        )
                    rent = inputs.rent(listing) if not blocked and listing.price_inr.value else None
                    growth = inputs.growth(listing) if not blocked else None
                    metrics = compute_metrics(
                        listing,
                        areas.get(listing.locality.value),
                        profile,
                        rent=rent,
                        growth=growth,
                        blocked_reason=blocked,
                    )
                    save_metrics(db, run_id, listing.id, metrics)
                    event.counts["metrics"] += 1
                    event.counts["roi_assessed"] += int(metrics.meets_target_roi is not None)
                    event.counts["investment_warnings"] = len(inputs.warnings)
                    event.message = (
                        f"Investment metrics saved for {event.counts['metrics']} candidates; "
                        f"{event.counts['roi_assessed']} ROI targets assessed; "
                        f"{len(inputs.warnings)} investment provider warnings. "
                        "Competitors pending (F-06)."
                    )
                    tracker.update_search_counts()
                    tracker.replace(event)
            tracker.update_search_counts()
            for stage, feature in NOT_BUILT.items():
                tracker.note(stage, f"Not built yet ({feature})")
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
