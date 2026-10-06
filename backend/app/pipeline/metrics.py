"""Stage 5c, enrich: investment metrics (CHECKLIST F-09).

Pure arithmetic over sourced inputs. No I/O, so it is unit-tested exhaustively. Every output
is `Sourced` with method `computed` and carries its inputs' sources forward.

    price_per_sqft     = price / size
    price_vs_area_pct  = (price_per_sqft / area_avg_price_per_sqft - 1) * 100
    rental_yield_pct   = est_monthly_rent * 12 / price * 100          (before any costs)
    price_growth_pct   = profile.expected_growth_pct if set, else the locality's
                         past-12-month change in price per sq ft (missing if not found)
    total_return_pct   = rental_yield_pct + price_growth_pct
    meets_target_roi   = value of GOAL_MEASURE[profile.goal] >= profile.target_roi_pct

There is no net yield or cap rate: both need cost assumptions (vacancy, maintenance, tax,
operating costs) that we would have to source (docs/decisions/0010-roi-definition.md).
"""

import math
import re
from collections.abc import Callable

from app.schemas.area import AreaIntel
from app.schemas.listing import Listing
from app.schemas.metrics import InvestmentMetrics
from app.schemas.profile import InvestorProfile
from app.schemas.provenance import ExtractionMethod, Sourced


def missing(note: str) -> Sourced:
    return Sourced(method=ExtractionMethod.COMPUTED, note=note)


def derived(inputs: list[Sourced], formula: Callable, note: str) -> Sourced[float]:
    if any(x.value is None or not math.isfinite(x.value) for x in inputs):
        return missing(
            note
            + "; required input unavailable; "
            + "; ".join(x.note for x in inputs if x.value is None and x.note)
        )
    sources = []
    for value in inputs:
        for source in value.sources:
            if source not in sources:
                sources.append(source)
    value = formula(*(x.value for x in inputs))
    if not math.isfinite(value):
        return missing(note + "; non-finite result")
    return Sourced(
        value=value,
        confidence=min(x.confidence for x in inputs),
        method=ExtractionMethod.COMPUTED,
        sources=sources,
        note=note + "; " + "; ".join(x.note for x in inputs if x.note),
    )


def compute_metrics(
    listing: Listing,
    area: AreaIntel | None,
    profile: InvestorProfile,
    *,
    rent: Sourced[int] | None = None,
    growth: Sourced[float] | None = None,
    blocked_reason: str | None = None,
) -> InvestmentMetrics:
    """Use full precision and preserve uncertainty; rent/growth I/O lives in enrichment."""
    price = listing.price_inr
    if price.note and re.search(r"range|starting price|lower bound", price.note, re.I):
        blocked_reason = (
            blocked_reason or "Final unit price is unconfirmed (range or starting price)."
        )
    if blocked_reason or price.value is None or price.value <= 0:
        price = missing(blocked_reason or "Positive sale price unavailable")
    size = listing.size_sqft
    if size.value is None or size.value <= 0:
        size = missing("Positive unit size unavailable")
    rate = derived([price, size], lambda p, s: p / s, "Sale price / unit size")
    if (
        rate.value is None
        and not blocked_reason
        and listing.price_per_sqft.value
        and math.isfinite(listing.price_per_sqft.value)
        and listing.price_per_sqft.value > 0
    ):
        rate = listing.price_per_sqft.model_copy(deep=True)
    benchmark = area.price_levels.get(listing.property_type.value) if area else None
    benchmark = benchmark or missing("No sourced benchmark for this locality and property type")
    if benchmark.value is not None and (not math.isfinite(benchmark.value) or benchmark.value <= 0):
        benchmark = missing("Area benchmark must be finite and positive")
    difference = derived(
        [rate, benchmark],
        lambda p, b: (p / b - 1) * 100,
        "Percentage above/below same-type locality benchmark; not a valuation",
    )
    rent = rent or missing("No comparable monthly rent quote")
    if rent.value is not None and rent.value <= 0:
        rent = missing("Monthly rent must be positive")
    yield_pct = derived(
        [rent, price],
        lambda r, p: r * 12 / p * 100,
        "Estimated gross rental yield before costs, vacancy and taxes",
    )
    if profile.expected_growth_pct is not None:
        growth = Sourced[float](
            value=profile.expected_growth_pct,
            confidence=1,
            method=ExtractionMethod.QUERY,
            note="Investor's growth assumption; not observed growth or a forecast",
        )
    growth = growth or missing("No sourced past-12-month price growth or investor assumption")
    if growth.value is not None and (
        not math.isfinite(growth.value) or not -100 <= growth.value <= 100
    ):
        growth = missing("Growth must be finite and between -100% and 100%")
    total = derived(
        [yield_pct, growth],
        lambda y, g: y + g,
        "Illustrative gross yield + growth; not a forecast or realised return",
    )
    measure = {"rental_yield": yield_pct, "price_growth": growth, "total_return": total}[
        profile.roi_measure
    ]
    meets = (
        None if blocked_reason or measure.value is None else measure.value >= profile.target_roi_pct
    )
    return InvestmentMetrics(
        price_per_sqft=rate,
        area_avg_price_per_sqft=benchmark,
        price_vs_area_pct=difference,
        est_monthly_rent_inr=rent,
        rental_yield_pct=yield_pct,
        price_growth_pct=growth,
        total_return_pct=total,
        roi_measure=profile.roi_measure,
        meets_target_roi=meets,
        target_roi_pct=profile.target_roi_pct,
        assessment_note=blocked_reason or (measure.note if measure.value is None else None),
    )
