"""Single-property and single-locality views (CHECKLIST F-07, F-05)."""

from sqlalchemy.orm import Session

from app.core.errors import NotFound, NotImplementedYet
from app.db.models import AreaIntelRow
from app.schemas.area import AreaIntel
from app.schemas.views import PropertyDetail


def get_property_detail(db: Session, listing_id: str) -> PropertyDetail:
    raise NotImplementedYet("F-07", "Property detail")


def get_area(db: Session, locality_key: str) -> AreaIntel:
    """The cached area for a key like `bengaluru/whitefield`, even if past its refresh time."""
    row = db.get(AreaIntelRow, locality_key)
    if row is None:
        raise NotFound(f"No area intelligence for {locality_key}")
    return AreaIntel.model_validate(row.data)
