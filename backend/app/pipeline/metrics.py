"""Stage 5c, enrich: investment metrics (CHECKLIST F-09, ADR 0010, ADR 0017).

Pure arithmetic over sourced inputs. No I/O, so it is unit-tested exhaustively. Every output
is `Sourced` with method `computed` and carries its inputs' sources forward. A missing input
gives a missing metric, never zero.

    price_per_sqft     = the listing's quoted rate, else price / size
    price_vs_area_pct  = (price_per_sqft / area price level - 1) * 100
    est_monthly_rent   = area rent per sq ft per month * size
    rental_yield_pct   = rent per sq ft per month * 12 / price_per_sqft * 100   (before costs;
                         needs no size, and none for a listing flagged too good to be true)
    price_growth_pct   = profile.expected_growth_pct if set, else the locality's
                         past-12-month change (missing if not found)
    total_return_pct   = rental_yield_pct + price_growth_pct
    meets_target_roi   = value of GOAL_MEASURE[profile.goal] >= profile.target_roi_pct

There is no net yield or cap rate: both need cost assumptions (vacancy, maintenance, tax,
operating costs) that we would have to source (docs/decisions/0010-roi-definition.md).
"""

from app.pipeline.quality import listing_rate
from app.schemas.listing import Listing, QualityFlagKind, Verification
from app.schemas.metrics import InvestmentMetrics
from app.schemas.profile import GOAL_MEASURE, InvestorProfile, ROIMeasure
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef


def _computed(value: float | None, note: str, *inputs: Sourced | None) -> Sourced:
    sources: list[SourceRef] = []
    for item in inputs:
        for source in item.sources if item is not None else []:
            if source not in sources:
                sources.append(source)
    known = [item.confidence for item in inputs if item is not None and item.value is not None]
    return Sourced(
        value=round(value, 2) if value is not None else None,
        confidence=min(known) if value is not None and known else 0.0,
        method=ExtractionMethod.COMPUTED,
        sources=sources,
        note=note,
    )


def compute_metrics(
    listing: Listing,
    verification: Verification | None,
    profile: InvestorProfile,
    price_level: Sourced[float] | None = None,
    rent_level: Sourced[float] | None = None,
    area_growth: Sourced[float] | None = None,
) -> InvestmentMetrics:
    rate = listing_rate(listing)
    rate_source = listing.price_per_sqft if listing.price_per_sqft.value else listing.price_inr
    level = price_level.value if price_level is not None else None
    rent = rent_level.value if rent_level is not None else None
    suspicious = verification is not None and any(
        flag.kind is QualityFlagKind.TOO_GOOD_TO_BE_TRUE for flag in verification.flags
    )

    vs_area = (rate / level - 1) * 100 if rate and level else None
    monthly_rent = rent * listing.size_sqft.value if rent and listing.size_sqft.value else None
    rental_yield = rent * 12 / rate * 100 if rent and rate and not suspicious else None

    if profile.expected_growth_pct is not None:
        growth = Sourced(
            value=profile.expected_growth_pct,
            confidence=1.0,
            method=ExtractionMethod.COMPUTED,
            note="the investor's expected growth (profile setting)",
        )
    else:
        growth = _computed(
            area_growth.value if area_growth is not None else None,
            "the locality's past-12-month change; past data, not a forecast",
            area_growth,
        )
    total = (
        rental_yield + growth.value
        if rental_yield is not None and growth.value is not None
        else None
    )
    metrics = InvestmentMetrics(
        price_per_sqft=_computed(rate, "quoted rate, else price ÷ size", rate_source),
        area_avg_price_per_sqft=_computed(level, "locality price level", price_level),
        price_vs_area_pct=_computed(vs_area, "price per sq ft vs the area level", price_level),
        est_monthly_rent_inr=Sourced(
            value=round(monthly_rent) if monthly_rent is not None else None,
            confidence=rent_level.confidence if monthly_rent is not None and rent_level else 0.0,
            method=ExtractionMethod.COMPUTED,
            sources=rent_level.sources if rent_level is not None else [],
            note="area rent per sq ft times size; an estimate, not this unit's rent",
        ),
        rental_yield_pct=_computed(
            rental_yield,
            "annual area rent ÷ price, before costs"
            + ("; not computed for a price flagged as implausible" if suspicious else ""),
            rent_level,
            price_level if rate is None else None,
        ),
        price_growth_pct=growth,
        total_return_pct=_computed(total, "rental yield + price growth", rent_level, growth),
        roi_measure=GOAL_MEASURE[profile.goal],
    )
    measured = measure_value(metrics)
    metrics.meets_target_roi = None if measured is None else measured >= profile.target_roi_pct
    return metrics


def measure_value(metrics: InvestmentMetrics) -> float | None:
    """The value the profile's target is compared with (ADR 0010)."""
    return {
        ROIMeasure.RENTAL_YIELD: metrics.rental_yield_pct,
        ROIMeasure.PRICE_GROWTH: metrics.price_growth_pct,
        ROIMeasure.TOTAL_RETURN: metrics.total_return_pct,
    }[metrics.roi_measure].value
