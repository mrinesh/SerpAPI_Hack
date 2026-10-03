"""Runs the pipeline end to end (CHECKLIST I-09). docs/PIPELINE.md has the stage-by-stage detail.

    plan -> fetch -> clean -> verify -> enrich -> rank

`start_run` creates a `pipeline_runs` row and hands `run_pipeline` to a background thread; the UI
polls `GET /api/runs/{id}` for `StageEvent`s. A stage failure marks the run failed but keeps
everything persisted so far, so a partial shortlist is still viewable.
"""

from app.core.errors import NotImplementedYet
from app.schemas.run import PipelineRun, PipelineStage

STAGE_ORDER: tuple[PipelineStage, ...] = (
    PipelineStage.PLAN,
    PipelineStage.FETCH,
    PipelineStage.CLEAN,
    PipelineStage.VERIFY,
    PipelineStage.ENRICH,
    PipelineStage.RANK,
)


def start_run(profile_id: str) -> PipelineRun:
    """Create the run record and schedule `run_pipeline` in the background."""
    raise NotImplementedYet("I-09", "Starting a pipeline run")


def run_pipeline(run_id: str) -> None:
    """Execute every stage for one run.

    Stage calls, in order:
      query_planner.plan_queries -> discovery.fetch_hits -> cleaning.normalize_hits
      -> verification.extract + verification.verify -> quality.flag_listing
      -> enrichment.area.get_area_intel (once per locality)
      -> enrichment.competitors.get_competitor_report (commercial only)
      -> metrics.compute_metrics -> ranking.rank
    """
    raise NotImplementedYet("I-09", "Pipeline execution")
