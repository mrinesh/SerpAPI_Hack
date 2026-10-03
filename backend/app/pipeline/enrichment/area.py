"""Stage 5a, enrich: area intelligence for one locality (CHECKLIST F-05).

Computed once per locality and cached in `area_intel` for `area_intel_ttl_hours`; every listing
in that locality reuses it. Sources, roughly 6 searches per new locality (confirm in S-03):
- google_maps "<locality>, Bengaluru"                 -> centre point (geocoding)
- google_maps "metro station" / "school" / "hospital" -> amenities near the centre
- google_news "<locality> Bengaluru"                  -> news, classified by `classify_news`
- google "<locality> property rates per sq ft"         -> price level and YoY change
- google_trends ["flats for rent <locality>", ...]     -> rental demand signal (F-05 P1 part)
"""

from app.core.errors import NotImplementedYet
from app.pipeline.context import PipelineContext
from app.schemas.area import AreaIntel


def locality_key(locality: str, city: str) -> str:
    """Normalised slug used as the cache key.

    ("Whitefield ", "Bengaluru") -> "bengaluru/whitefield"
    """
    raise NotImplementedYet("F-05", "Locality key normalisation")


def get_area_intel(ctx: PipelineContext, locality: str) -> AreaIntel:
    raise NotImplementedYet("F-05", "Area intelligence")
