"""Listing quality flags: duplicate, too-good-to-be-true, missing data (CHECKLIST F-12).

Rule-based and explainable on purpose; each flag's `reason` is shown to the investor.
- too_good_to_be_true: price per sq ft far below the locality average (threshold set in F-12);
  this also catches snippet prices that are really rents (S-01 saw "₹3.6 Lac … ₹75 /sqft");
- duplicate: the same candidate quoted by several pages, merged in cleaning;
- missing_price / missing_size: from cleaning and extraction.
There is no "stale" flag: search results carry no posted dates (S-01).
"""

from app.core.errors import NotImplementedYet
from app.schemas.area import AreaIntel
from app.schemas.listing import Listing, QualityFlag


def flag_listing(listing: Listing, area: AreaIntel | None) -> list[QualityFlag]:
    raise NotImplementedYet("F-12", "Listing quality flags")
