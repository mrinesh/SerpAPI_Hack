"""Single-property and single-locality views (CHECKLIST F-07, F-05)."""

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFound, NotImplementedYet
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
    try:
        return AreaIntel.model_validate(row.data)
    except ValidationError as exc:
        # Never trust or silently repair a corrupt row on a read; the next run rebuilds it.
        raise AppError(
            f"The cached area for {locality_key} is unreadable; run a search to rebuild it.",
            details={"locality_key": locality_key, "operation": "area_cache_read"},
        ) from exc
