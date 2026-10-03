"""Single-property and single-locality views (CHECKLIST F-07, F-05)."""

from sqlalchemy.orm import Session

from app.core.errors import NotImplementedYet
from app.schemas.area import AreaIntel
from app.schemas.views import PropertyDetail


def get_property_detail(db: Session, listing_id: str) -> PropertyDetail:
    raise NotImplementedYet("F-07", "Property detail")


def get_area(db: Session, locality_key: str) -> AreaIntel:
    raise NotImplementedYet("F-05", "Reading area intelligence")
