"""Listing quality flags: stale, duplicate, too-good-to-be-true (CHECKLIST F-12).

Rule-based and explainable on purpose; each flag's `reason` is shown to the investor.
- too_good_to_be_true: price per sq ft far below the locality average (threshold set in F-12);
- stale: posted date older than N days, or the portal page says "sold" / "inactive";
- duplicate: same property listed under several URLs, kept but merged in cleaning;
- not_a_listing / missing_price / missing_size: from cleaning and extraction.
"""

from app.core.errors import NotImplementedYet
from app.schemas.area import AreaIntel
from app.schemas.listing import Listing, QualityFlag


def flag_listing(listing: Listing, area: AreaIntel | None) -> list[QualityFlag]:
    raise NotImplementedYet("F-12", "Listing quality flags")
