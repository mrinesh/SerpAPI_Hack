"""Stage 2, fetch: run planned queries through the SerpApi gateway (CHECKLIST F-02).

Turns `organic_results` (google) and `local_results` (google_maps) into `RawSearchHit`s, keeping
`rich_snippet`, `gps_coordinates` and `search_metadata.id` for provenance. Stops issuing live
searches once the run budget is spent and records that in the stage event.
"""

from app.core.errors import NotImplementedYet
from app.pipeline.context import PipelineContext
from app.pipeline.query_planner import PlannedQuery
from app.schemas.listing import RawSearchHit


def fetch_hits(ctx: PipelineContext, queries: list[PlannedQuery]) -> list[RawSearchHit]:
    raise NotImplementedYet("F-02", "Discovery fetch")
