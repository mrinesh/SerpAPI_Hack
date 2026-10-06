"""Single-property and single-locality views (CHECKLIST F-07, F-05)."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import InvalidInput, NotFound, NotImplementedYet
from app.db.models import AreaIntelRow
from app.pipeline.enrichment.area import as_utc, read_cached_area
from app.pipeline.enrichment.area import locality_key as canonical_key
from app.schemas.area import AreaIntel
from app.schemas.views import PropertyDetail


def get_property_detail(db: Session, listing_id: str) -> PropertyDetail:
    raise NotImplementedYet("F-07", "Property detail")


def get_area(db: Session, locality_key: str) -> AreaIntel:
    """Read only: GET never spends search credits. Rerun a profile to refresh expired data."""
    parts = locality_key.split("/")
    if len(parts) != 2:
        raise InvalidInput(["locality_key"], "Expected city/locality")
    city, locality = parts
    key = canonical_key(locality, city)
    row = db.get(AreaIntelRow, key)
    if row is None:
        raise NotFound(f"Area {key} has not been enriched; run a profile for this locality.")
    area = read_cached_area(row)
    return area.model_copy(
        update={"cache_hit": True, "stale": as_utc(area.expires_at) <= datetime.now(UTC)}
    )
