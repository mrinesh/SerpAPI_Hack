"""Suggested target ROI for a profile being written (ADR 0018).

The suggestion is the market's typical value of the goal's measure (ADR 0010) for the chosen
localities and property types, adjusted for risk appetite and rounded:
- rental yield: area rent per sq ft per month * 12 / area price per sq ft (ADR 0014, 0017);
- price growth: the average yearly change over several years (`area.long_run_growth`), not one
  boom year;
- total return: both added.
Every number comes from the pipeline's sourced lookups, which are cached by the SerpApi gateway
and the LLM cache; values already in `area_intel` are used first. No data means no suggestion.
"""

import statistics
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.config import Settings
from app.core.errors import AppError
from app.db.models import AreaIntelRow
from app.integrations.llm.factory import get_llm
from app.integrations.serpapi.gateway import SerpApiGateway
from app.pipeline.enrichment.area import locality_key, long_run_growth
from app.pipeline.enrichment.price_level import searched_level
from app.pipeline.enrichment.rent_level import rent_level
from app.pipeline.query_planner import QUERY_WORDS
from app.reference import Market
from app.schemas.area import AreaIntel
from app.schemas.profile import GOAL_MEASURE, PropertyType, RiskAppetite, ROIMeasure
from app.schemas.provenance import ExtractionMethod, Sourced
from app.schemas.target import TargetSuggestion, TargetSuggestionIn, TargetSuggestionPart

# A target relative to what the market typically gives: a conservative investor aims a little
# lower (more candidates meet it), an aggressive one higher (ADR 0018).
RISK_FACTORS: dict[RiskAppetite, float] = {
    RiskAppetite.CONSERVATIVE: 0.9,
    RiskAppetite.BALANCED: 1.0,
    RiskAppetite.AGGRESSIVE: 1.15,
}
STEP = 0.5  # suggestions are rounded to the nearest half percent
MEASURE_WORDS = {
    ROIMeasure.RENTAL_YIELD: "rental yield before costs",
    ROIMeasure.PRICE_GROWTH: "average yearly price growth over recent years",
    ROIMeasure.TOTAL_RETURN: "rental yield before costs plus average yearly price growth",
}


def round_target(value: float) -> float:
    return max(STEP, round(value / STEP) * STEP)


def area_yield(rent: Sourced[float] | None, price: Sourced[float] | None) -> Sourced[float] | None:
    if rent is None or price is None or not rent.value or not price.value:
        return None
    return Sourced(
        value=round(rent.value * 12 / price.value * 100, 2),
        confidence=min(rent.confidence, price.confidence),
        method=ExtractionMethod.COMPUTED,
        sources=[*rent.sources, *price.sources],
        note="area rent per sq ft x 12 / area price per sq ft; before costs",
    )


def typical_value(
    measure: ROIMeasure, yield_: Sourced[float] | None, growth: Sourced[float] | None
) -> Sourced[float] | None:
    if measure is ROIMeasure.RENTAL_YIELD:
        return yield_
    if measure is ROIMeasure.PRICE_GROWTH:
        return growth
    if yield_ is None or growth is None:
        return None
    return Sourced(
        value=round(yield_.value + growth.value, 2),
        confidence=min(yield_.confidence, growth.confidence),
        method=ExtractionMethod.COMPUTED,
        sources=[*yield_.sources, *growth.sources],
        note="rental yield + average yearly price growth",
    )


def combine(
    measure: ROIMeasure, parts: list[TargetSuggestionPart], risk: RiskAppetite
) -> TargetSuggestion:
    if not parts:
        return TargetSuggestion(
            target_roi_pct=None,
            measure=measure,
            typical_pct=None,
            basis="No sourced data yet for these localities; enter your own target.",
        )
    typical = round(statistics.median(part.typical.value for part in parts), 2)
    target = round_target(typical * RISK_FACTORS[risk])
    where = "; ".join(
        f"{QUERY_WORDS[part.property_type]} in {part.locality} {part.typical.value:.1f}%"
        for part in parts
    )
    adjusted = {
        RiskAppetite.CONSERVATIVE: " Set a little lower for a conservative appetite.",
        RiskAppetite.BALANCED: "",
        RiskAppetite.AGGRESSIVE: " Set a little higher for an aggressive appetite.",
    }[risk]
    return TargetSuggestion(
        target_roi_pct=target,
        measure=measure,
        typical_pct=typical,
        basis=f"Typical {MEASURE_WORDS[measure]}: {where}.{adjusted}",
        parts=parts,
    )


def suggest_target(
    db: Session, settings: Settings, market: Market, data: TargetSuggestionIn
) -> TargetSuggestion:
    measure = GOAL_MEASURE[data.goal]
    # The lookups need only these four context fields; there is no run or profile yet.
    ctx = SimpleNamespace(
        db=db, settings=settings, serp=SerpApiGateway(settings, db), llm=get_llm(settings, db),
        run_id=None,
    )  # fmt: skip
    parts: list[TargetSuggestionPart] = []
    for slug in data.localities:
        place = market.locality(slug)
        name = place.name if place else slug
        row = db.get(AreaIntelRow, locality_key(name, market.city))
        cached = AreaIntel.model_validate(row.data) if row else None
        growth = None
        if measure is not ROIMeasure.RENTAL_YIELD:
            growth = long_run_growth(ctx, name, market)
        for kind in data.property_types:
            yield_ = None
            if measure is not ROIMeasure.PRICE_GROWTH:
                price = (cached.price_levels.get(kind) if cached else None) or searched_level(
                    ctx, market, name, PropertyType(kind)
                )
                rent = (cached.rent_levels.get(kind) if cached else None) or _rent(
                    ctx, market, name, PropertyType(kind)
                )
                yield_ = area_yield(rent, price)
            typical = typical_value(measure, yield_, growth)
            if typical is not None and typical.value is not None:
                parts.append(
                    TargetSuggestionPart(locality=name, property_type=kind, typical=typical)
                )
    return combine(measure, parts, data.risk_appetite)


def _rent(ctx, market: Market, name: str, kind: PropertyType) -> Sourced[float] | None:
    try:
        return rent_level(ctx, market, name, kind)
    except AppError:
        return None  # a suggestion never fails; the part is simply missing
