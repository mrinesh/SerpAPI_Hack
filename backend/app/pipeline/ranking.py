"""Stage 6, rank: composite score and plain-language reasons (CHECKLIST F-04, ADR 0015).

The score is a weighted blend computed in code (not by the LLM) so it is reproducible:
relevance (the F-03 match score), value (price per sq ft against the locality price level),
evidence (confidence and data completeness), ROI vs target (F-09) and area signals (F-05), minus
quality-flag penalties. Weights depend on `profile.goal` and `profile.risk_appetite`; a component
that is not available (ROI and area signals until F-09 / F-05 exist) is left out and the others
are renormalised. `score_breakdown` exposes the points each component contributed.

Every ranked candidate gets a reason written by code. The top `EXPLAIN_TOP` also get one from
the LLM (`explain_recommendation`), which may only quote the display figures it is given: a
reason quoting any other number falls back to the code reason (ADR 0008).
"""

from pydantic import BaseModel

from app.integrations.llm.base import ModelTier
from app.pipeline.context import PipelineContext
from app.pipeline.enrichment.area import growth_text, listing_access
from app.pipeline.grounding import allowed_numbers, grounded
from app.pipeline.metrics import measure_value
from app.pipeline.quality import listing_rate
from app.pipeline.verification import listing_input, prompt_for
from app.reference import Market
from app.schemas.area import AreaAccess, AreaIntel
from app.schemas.common import Level
from app.schemas.listing import Listing, MatchVerdict, QualityFlagKind, Verification
from app.schemas.metrics import InvestmentMetrics
from app.schemas.profile import InvestmentGoal, InvestorProfile, RiskAppetite
from app.schemas.provenance import Sourced
from app.schemas.recommendation import Recommendation

COMPONENTS = ("relevance", "roi", "value", "evidence", "area")
# Percentage points per component, by investment goal (ADR 0015).
WEIGHTS: dict[InvestmentGoal, dict[str, float]] = {
    InvestmentGoal.RENTAL_INCOME: {
        "relevance": 40, "roi": 25, "value": 15, "evidence": 15, "area": 5,
    },
    InvestmentGoal.APPRECIATION: {
        "relevance": 35, "roi": 20, "value": 25, "evidence": 10, "area": 10,
    },
    InvestmentGoal.BALANCED: {
        "relevance": 40, "roi": 20, "value": 20, "evidence": 12, "area": 8,
    },
}  # fmt: skip
# Conservative investors weigh evidence more; aggressive ones weigh a below-market price more.
RISK_SHIFTS: dict[RiskAppetite, dict[str, float]] = {
    RiskAppetite.CONSERVATIVE: {"relevance": -5, "value": -5, "evidence": 10},
    RiskAppetite.BALANCED: {},
    RiskAppetite.AGGRESSIVE: {"evidence": -5, "value": 5},  # evidence never drops below 5
}
# Area access (ADR 0016): metro 100 at <= 0.5 km falling to 0 at 4 km; schools and hospitals
# found within 3 km, full marks at 3 each. Price growth is F-09's (ROI), so it is not scored here.
METRO_FULL_KM, METRO_ZERO_KM = 0.5, 4.0
NEARBY_FULL = 3
AREA_PARTS = {"metro": 0.5, "schools": 0.25, "hospitals": 0.25}
ROI_FULL_AT = 1.5  # ROI points: full marks at 1.5x the investor's target (ADR 0017)
VALUE_SLOPE = 125  # value score points per 100% of the area level: 0.6x -> 100, 1.4x -> 0
FLAG_PENALTY = 25  # points off per high-severity quality flag
EXPLAIN_TOP = 5  # LLM-written reasons per run
VERDICT_WORDS = {
    MatchVerdict.STRONG: "strong match",
    MatchVerdict.PARTIAL: "partial match",
    MatchVerdict.WEAK: "weak match",
}

LevelKey = tuple[str | None, object]


class Explanation(BaseModel):
    """Output schema of the `explain_recommendation` prompt."""

    reason: str
    highlights: list[str]
    risks: list[str]


# --- scoring (pure) -----------------------------------------------------------------------


def weights_for(goal: InvestmentGoal, risk: RiskAppetite) -> dict[str, float]:
    weights = dict(WEIGHTS[goal])
    for component, shift in RISK_SHIFTS[risk].items():
        weights[component] += shift
    return weights


def is_too_good(verification: Verification) -> bool:
    return any(flag.kind is QualityFlagKind.TOO_GOOD_TO_BE_TRUE for flag in verification.flags)


def value_score(
    listing: Listing, verification: Verification, level: Sourced[float] | None
) -> float | None:
    """50 at the area level, higher when cheaper. None when it cannot be judged, or when the
    price is flagged as implausible (a suspicious bargain must not score as value)."""
    rate = listing_rate(listing)
    if rate is None or level is None or not level.value or is_too_good(verification):
        return None
    return _clamp(50 + (1 - rate / level.value) * VALUE_SLOPE)


def evidence_score(listing: Listing, verification: Verification) -> float:
    facts = (listing.price_inr.value, listing.size_sqft.value, listing.status.value)
    completeness = sum(fact is not None for fact in facts) / len(facts)
    return _clamp(100 * (0.5 * verification.confidence + 0.5 * completeness))


def area_score(access: AreaAccess | None) -> float | None:
    if access is None:
        return None
    metro = 0.0
    if access.metro_km is not None:
        span = METRO_ZERO_KM - METRO_FULL_KM
        metro = _clamp(100 * (METRO_ZERO_KM - access.metro_km) / span)
    parts = {
        "metro": metro,
        "schools": min(access.schools_3km, NEARBY_FULL) / NEARBY_FULL * 100,
        "hospitals": min(access.hospitals_3km, NEARBY_FULL) / NEARBY_FULL * 100,
    }
    return sum(AREA_PARTS[name] * value for name, value in parts.items())


def roi_score(metrics: InvestmentMetrics | None, target: float) -> float | None:
    """Proportional to the goal's measure: 0 at 0%, 66.7 at the target, 100 at 1.5x it."""
    measured = measure_value(metrics) if metrics is not None else None
    if measured is None:
        return None
    if target <= 0:
        return 100.0 if measured >= 0 else 0.0
    return _clamp(measured / (ROI_FULL_AT * target) * 100)


def components(
    listing: Listing,
    verification: Verification,
    level: Sourced[float] | None,
    access: AreaAccess | None = None,
    roi: float | None = None,
) -> dict[str, float | None]:
    return {
        "relevance": float(verification.match_score),
        "roi": roi,
        "value": value_score(listing, verification, level),
        "evidence": evidence_score(listing, verification),
        "area": area_score(access),
    }


def composite(
    parts: dict[str, float | None], weights: dict[str, float], penalty: float
) -> tuple[float, dict[str, float | None]]:
    """Score and breakdown: available components renormalised to 100%, minus the penalty."""
    available = {name: value for name, value in parts.items() if value is not None}
    total_weight = sum(weights[name] for name in available)
    breakdown: dict[str, float | None] = {
        name: (
            round(weights[name] / total_weight * parts[name], 1)
            if parts[name] is not None
            else None
        )
        for name in COMPONENTS
    }
    breakdown["flag_penalty"] = -penalty
    score = sum(value for value in breakdown.values() if value is not None)
    return round(_clamp(score), 1), breakdown


def flag_penalty(verification: Verification) -> float:
    return FLAG_PENALTY * sum(flag.severity is Level.HIGH for flag in verification.flags)


def score_candidates(
    profile: InvestorProfile,
    checked: list[tuple[Listing, Verification]],
    levels: dict[LevelKey, Sourced[float]],
    market: Market | None = None,
    areas: dict[str, AreaIntel] | None = None,
    metrics: dict[str, InvestmentMetrics] | None = None,
) -> list[Recommendation]:
    """Rank every checked candidate that was not rejected; each gets a code-written reason."""
    weights = weights_for(profile.goal, profile.risk_appetite)
    scored = []
    for listing, verification in checked:
        if verification.verdict is MatchVerdict.REJECT:
            continue
        level = level_for(levels, listing)
        access = listing_access(
            listing.location.value, (areas or {}).get(listing.locality.value or "")
        )
        found = (metrics or {}).get(listing.id)
        roi = roi_score(found, profile.target_roi_pct)
        score, breakdown = composite(
            components(listing, verification, level, access, roi),
            weights,
            flag_penalty(verification),
        )
        scored.append((score, listing, verification, breakdown, access, found))
    scored.sort(key=lambda item: (-item[0], item[1].price_inr.value or 0, item[1].id))
    total = len(scored)
    recommendations = []
    for rank, (score, listing, verification, breakdown, access, found) in enumerate(
        scored, start=1
    ):
        recommendation = Recommendation(
            rank=rank,
            listing=listing,
            verification=verification,
            score=score,
            score_breakdown=breakdown,
            access=access,
            metrics=found,
            reason="",
        )
        recommendation.reason = code_reason(
            recommendation,
            total,
            level_for(levels, listing),
            place_name(market, listing),
            profile.target_roi_pct,
        )
        recommendations.append(recommendation)
    return recommendations


# --- reasons ------------------------------------------------------------------------------


def inr_short(value: int) -> str:
    """₹76 L, ₹1.15 Cr, ₹45,000."""
    if value >= 10_000_000:
        return f"₹{_compact(value / 10_000_000)} Cr"
    if value >= 100_000:
        return f"₹{_compact(value / 100_000)} L"
    return f"₹{value:,}"


def code_reason(
    recommendation: Recommendation,
    total: int,
    level: Sourced[float] | None,
    place: str,
    target_roi: float | None = None,
) -> str:
    verification = recommendation.verification
    parts = [
        f"#{recommendation.rank} of {total}: {VERDICT_WORDS[verification.verdict]}, "
        f"relevance {verification.match_score}/100."
    ]
    figures = display_figures(recommendation, total, level, place, None)
    if is_too_good(verification):
        parts.append(f"Quoted at {figures['price']}, which looks implausibly low for the area.")
    elif "price_vs_area" in figures:
        parts.append(
            f"Quoted at {figures['price']}, {figures['price_vs_area']} {place}'s "
            f"{figures['area_level']} level."
        )
    elif "price" in figures:
        parts.append(f"Quoted at {figures['price']}.")
    else:
        parts.append("No price is quoted yet.")
    if (yield_text := _yield_text(recommendation)) and target_roi is not None:
        verdict = "meets" if recommendation.metrics.meets_target_roi else "below"
        if recommendation.metrics.roi_measure == "rental_yield":
            parts.append(f"Estimated {yield_text}, {verdict} the {_compact(target_roi)}% target.")
        else:
            parts.append(f"Estimated {yield_text}.")
    return " ".join(parts)


def _yield_text(recommendation: Recommendation) -> str | None:
    metrics = recommendation.metrics
    if metrics is None or metrics.rental_yield_pct.value is None:
        return None
    return f"rental yield {metrics.rental_yield_pct.value:.1f}% before costs"


def display_figures(
    recommendation: Recommendation,
    total: int,
    level: Sourced[float] | None,
    place: str,
    profile: InvestorProfile | None,
    growth: Sourced[float] | None = None,
) -> dict[str, str]:
    """The only figures an explanation may quote, already formatted for display."""
    listing, verification = recommendation.listing, recommendation.verification
    figures = {
        "name": listing.name,
        "rank": f"#{recommendation.rank} of {total}",
        "score": f"{_compact(recommendation.score)}/100",  # as the UI shows it, e.g. 74.5
        "relevance": f"{verification.match_score}/100",
        "verdict": VERDICT_WORDS[verification.verdict],
    }
    if listing.price_inr.value:
        figures["price"] = inr_short(listing.price_inr.value)
    if listing.size_sqft.value:
        figures["size"] = f"{listing.size_sqft.value:,.0f} sq ft"
    if listing.bedrooms.value:
        figures["bedrooms"] = f"{listing.bedrooms.value} BHK"
    rate = listing_rate(listing)
    if rate:
        figures["rate"] = f"₹{rate:,.0f}/sq ft"
    if level is not None and level.value:
        figures["area_level"] = f"₹{level.value:,.0f}/sq ft"
        if rate and not is_too_good(verification):
            change = round((rate / level.value - 1) * 100)
            figures["price_vs_area"] = (
                "in line with" if change == 0 else
                f"{abs(change)}% {'below' if change < 0 else 'above'}"
            )  # fmt: skip
    access = recommendation.access
    if access is not None:
        where = "" if access.measured_from == "listing" else f" from the centre of {place}"
        if access.metro_km is not None:
            figures["nearest_metro"] = f"{access.metro_name}, {access.metro_km:g} km{where}"
        figures["schools"] = f"{access.schools_3km} schools found within 3 km"
        figures["hospitals"] = f"{access.hospitals_3km} hospitals found within 3 km"
    if text := growth_text(growth):
        figures["price_growth"] = f"{place}: {text}"
    metrics = recommendation.metrics
    if metrics is not None:
        if yield_text := _yield_text(recommendation):
            figures["rental_yield"] = yield_text
        if metrics.est_monthly_rent_inr.value:
            figures["est_rent"] = f"about {inr_short(metrics.est_monthly_rent_inr.value)} a month"
        if metrics.total_return_pct.value is not None:
            figures["total_return"] = f"total return {metrics.total_return_pct.value:.1f}%"
        if metrics.meets_target_roi is not None and profile is not None:
            figures["target_check"] = (
                f"{'meets' if metrics.meets_target_roi else 'below'} the "
                f"{_compact(profile.target_roi_pct)}% target"
            )
    if profile is not None:
        figures["budget"] = f"up to {inr_short(profile.budget_max_inr)}"
        figures["target_roi"] = f"{_compact(profile.target_roi_pct)}% target ROI"
    figures["place"] = place
    return figures


def guard(
    explanation: Explanation, figures: dict[str, str], fallback: str
) -> tuple[str, list[str], list[str], bool]:
    allowed = allowed_numbers(figures)
    explained = bool(explanation.reason.strip()) and grounded(explanation.reason, allowed)
    keep = [item for item in explanation.highlights[:3] if item.strip() and grounded(item, allowed)]
    risks = [item for item in explanation.risks[:3] if item.strip() and grounded(item, allowed)]
    return (explanation.reason.strip() if explained else fallback), keep, risks, explained


def explain(
    ctx: PipelineContext,
    recommendation: Recommendation,
    total: int,
    level: Sourced[float] | None,
    place: str,
    growth: Sourced[float] | None = None,
) -> Recommendation:
    figures = display_figures(recommendation, total, level, place, ctx.profile, growth)
    profile = ctx.profile.model_dump(
        mode="json", exclude={"id", "name", "created_at", "updated_at"}
    )
    verification = recommendation.verification.model_dump(
        mode="json", include={"verdict", "matched_criteria", "mismatches", "missing_data", "flags"}
    )
    strengths = [
        name
        for name, points in sorted(
            recommendation.score_breakdown.items(), key=lambda item: -(item[1] or 0)
        )
        if name != "flag_penalty" and points
    ]
    explanation = ctx.llm.generate_structured(
        task="explain_recommendation",
        prompt=prompt_for(
            "explain_recommendation",
            profile=profile,
            listing=listing_input(recommendation.listing),
            verification=verification,
            figures=figures,
            strongest_score_parts=strengths,
        ),
        schema=Explanation,
        tier=ModelTier.LITE,
    )
    reason, highlights, risks, explained = guard(explanation, figures, recommendation.reason)
    return recommendation.model_copy(
        update={"reason": reason, "highlights": highlights, "risks": risks, "explained": explained}
    )


# --- helpers ------------------------------------------------------------------------------


def level_for(levels: dict[LevelKey, Sourced[float]], listing: Listing) -> Sourced[float] | None:
    return levels.get((listing.locality.value, listing.property_type.value))


def place_name(market: Market | None, listing: Listing) -> str:
    slug = listing.locality.value or ""
    locality = market.locality(slug) if market else None
    return locality.name if locality else slug.replace("-", " ").title()


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _compact(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")
