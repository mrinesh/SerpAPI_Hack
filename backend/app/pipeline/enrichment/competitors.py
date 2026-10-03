"""Stage 5b, enrich: competitor analysis for commercial properties (CHECKLIST F-06).

Only runs when `profile.segment == commercial` and `profile.business_category` is set.
- google_maps "<category>" near the property -> competitors, ratings, review counts, density;
- google_maps_reviews for the top-N competitors -> review text for `competitor_gaps` (F-06b, P1).
Cached in `competitor_reports` keyed by hash(rounded centre, category, radius).
"""

from app.core.errors import NotImplementedYet
from app.pipeline.context import PipelineContext
from app.schemas.common import GeoPoint
from app.schemas.competitor import CompetitorReport


def get_competitor_report(
    ctx: PipelineContext, center: GeoPoint, category: str, radius_km: float = 1.0
) -> CompetitorReport:
    raise NotImplementedYet("F-06", "Competitor analysis")
