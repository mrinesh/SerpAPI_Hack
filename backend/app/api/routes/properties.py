from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.area import AreaIntel
from app.schemas.views import PropertyDetail
from app.services import properties

router = APIRouter(tags=["properties"])


@router.get("/properties/{listing_id}")
def get_property(listing_id: str, db: DbSession, run_id: str | None = None) -> PropertyDetail:
    """The listing as `run_id` judged it; without it, the latest run that found it."""
    return properties.get_property_detail(db, listing_id, run_id)


@router.get("/areas/{locality_key:path}")
def get_area(locality_key: str, db: DbSession) -> AreaIntel:
    """`locality_key` looks like "bengaluru/whitefield"."""
    return properties.get_area(db, locality_key)
