"""Listing quality flags: too-good-to-be-true and missing data (CHECKLIST F-12, ADR 0014).

Rule-based and explainable on purpose; each flag's `reason` is shown to the investor.
- too_good_to_be_true: price per sq ft below `TOO_LOW_SHARE` of the locality's price level
  (`enrichment/price_level.py`); this also catches snippet prices that are really rents
  (S-01 saw "₹3.6 Lac … ₹75 /sqft"). No benchmark means no flag: there is no flat rate;
- missing_price / missing_size: from cleaning and extraction;
- location_mismatch: the listing's own text names other localities and not the one searched
  (I-12, ADR 0024). High when none of them is in the profile (it contradicts a hard
  constraint, unconfirmed); medium when one is (the listing is mislabelled, not out of area).
Duplicates are merged in cleaning, so they need no flag. There is no "stale" flag: search
results carry no posted dates (S-01).
"""

import re

from app.reference import Market
from app.schemas.common import Level
from app.schemas.listing import Listing, QualityFlag, QualityFlagKind
from app.schemas.provenance import ExtractionMethod, Sourced

TOO_LOW_SHARE = 0.4  # a sale rate under 40% of the area's level is implausible (ADR 0014)


_BOUND = re.compile(r"range|starting price|lower bound", re.I)


def price_is_bound(listing: Listing) -> bool:
    """True when the quote is a range or a starting price, not a final unit price."""
    return bool(listing.price_inr.note and _BOUND.search(listing.price_inr.note))


def listing_rate(listing: Listing) -> float | None:
    if listing.price_per_sqft.value:
        return listing.price_per_sqft.value
    if listing.price_inr.value and listing.size_sqft.value:
        return listing.price_inr.value / listing.size_sqft.value
    return None


def flag_listing(listing: Listing, benchmark: Sourced[float] | None) -> list[QualityFlag]:
    flags: list[QualityFlag] = []
    rate = listing_rate(listing)
    if rate is not None and benchmark is not None and benchmark.value:
        share = rate / benchmark.value
        if share < TOO_LOW_SHARE:
            percent = f"{share:.1%}" if share < 0.1 else f"{share:.0%}"
            flags.append(
                QualityFlag(
                    kind=QualityFlagKind.TOO_GOOD_TO_BE_TRUE,
                    severity=Level.HIGH,
                    reason=(
                        f"₹{rate:,.0f}/sq ft is {percent} of the area's typical "
                        f"₹{benchmark.value:,.0f}/sq ft ({_origin(benchmark)}). "
                        "It may be a monthly rent or a data error."
                    ),
                )
            )
    if listing.price_inr.value is None:
        flags.append(
            QualityFlag(
                kind=QualityFlagKind.MISSING_PRICE,
                severity=Level.LOW,
                reason="No asking price is quoted.",
            )
        )
    if listing.size_sqft.value is None:
        flags.append(
            QualityFlag(
                kind=QualityFlagKind.MISSING_SIZE,
                severity=Level.LOW,
                reason="No size is quoted.",
            )
        )
    return flags


def location_flag(
    listing: Listing, profile_localities: list[str], market: Market | None
) -> QualityFlag | None:
    named, searched = listing.named_localities, listing.locality.value
    if not named or searched is None or searched in named:
        return None

    def name(slug: str) -> str:
        place = market.locality(slug) if market else None
        return place.name if place else slug

    names = ", ".join(name(slug) for slug in named)
    if any(slug in profile_localities for slug in named):
        return QualityFlag(
            kind=QualityFlagKind.LOCATION_MISMATCH,
            severity=Level.MEDIUM,
            reason=(
                f"The result text places it in {names}, not {name(searched)} where it "
                "was found; that is also one of your localities."
            ),
        )
    return QualityFlag(
        kind=QualityFlagKind.LOCATION_MISMATCH,
        severity=Level.HIGH,
        reason=(
            f"The result text places it in {names}, not {name(searched)}, the locality "
            "searched. It may be outside your localities."
        ),
    )


def _origin(benchmark: Sourced[float]) -> str:
    if benchmark.method is ExtractionMethod.COMPUTED:
        return benchmark.note or "rates quoted in this run"
    source = benchmark.sources[0] if benchmark.sources else None
    return (source.title or source.url or "search result") if source else "search result"
