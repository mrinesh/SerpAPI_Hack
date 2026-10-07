"""Developing-area signals (ADR 0025): code measures search growth, checks it against observed
prices and recent infrastructure news, and ranks research priorities; DeepSeek only reviews the
evidence and picks cited, unconfirmed explanations. Display only: nothing here feeds the
property score. Ported from gscode007's `feature/search-driven-area-insights` branch onto main's
area intelligence (`AreaIntel.price_growth_pct` and classified `AreaIntel.news`)."""

import re
import statistics
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from app.core.errors import AppError, UpstreamError
from app.integrations.llm.base import ModelTier
from app.pipeline.context import PipelineContext
from app.pipeline.enrichment.search_history import app_history
from app.pipeline.verification import prompt_for
from app.schemas.area import AreaIntel, AreaIssue
from app.schemas.development import AreaDevelopment, DevelopmentHypothesis, SearchMomentum
from app.schemas.provenance import Sourced

WEIGHTS = {
    "rental_interest": 35,
    "locality_interest": 15,
    "app_searches": 15,
    "observed_prices": 15,
    "infrastructure": 20,
}
DRIVERS = {
    "transport": (
        r"metro|rail|road|flyover|traffic|transport|connectivity|bmrcl|purple line|footpath|ramp",
        "Transport-related reports could be affecting interest in this locality.",
    ),
    "employment": (
        r"office|job|employment|business|tech|company|companies",
        "Employment or business-related news could be influencing interest.",
    ),
    "housing": (
        r"housing|residential|apartment|flat|property|real estate|developer",
        "Housing or property announcements could be influencing local research activity.",
    ),
    "policy": (
        r"policy|regulation|approval|government|tax|zoning|bbmp|bda",
        "Policy or civic changes could be influencing local research activity.",
    ),
    "amenities": (
        r"school|hospital|mall|park|water|service|amenit|passport|waste",
        "Reports about local services could be influencing interest.",
    ),
    "publicity": (r".+", "Local news coverage itself could be drawing search attention."),
}


class HypothesisSelection(BaseModel):
    driver: Literal["transport", "employment", "housing", "policy", "amenities", "publicity"]
    news_index: int = Field(ge=0)
    quote: str
    confidence: float = Field(ge=0, le=1)


class DevelopmentReview(BaseModel):
    review: Literal["consistent", "mixed", "inconclusive"]
    hypotheses: list[HypothesisSelection] = Field(default_factory=list, max_length=3)


def qualified(signal: SearchMomentum) -> bool:
    return (
        signal.usable
        and signal.signal == "rising"
        and signal.annual_change_pct is not None
        and signal.annual_change_pct >= 10
    )


def momentum_score(signal: SearchMomentum) -> float:
    if not qualified(signal):
        return 0
    return min(100, max(0, signal.quarter_change_pct or 0))


PRICE_KEY = "Past 12 months"  # main's area price change is per locality, not per type


def observed_growth(area: AreaIntel) -> dict[str, Sourced[float]]:
    """The area's sourced past-12-month price change, when a search result stated one."""
    growth = area.price_growth_pct
    if growth is None or growth.value is None or growth.method == "query":
        return {}
    return {PRICE_KEY: growth}


def assess(
    area: AreaIntel,
    public: list[SearchMomentum],
    app: SearchMomentum,
    growth: dict[str, Sourced[float]],
    *,
    now: datetime,
) -> AreaDevelopment:
    observed = {
        kind: value
        for kind, value in growth.items()
        if value.value is not None and value.method != "query"
    }
    # Distinct recent positive infrastructure reports that DeepSeek labelled (ADR 0020), not
    # keyword mentions, undated or older-than-a-year items.
    infra_count = len(
        {
            n.url
            for n in area.news
            if n.classified
            and n.topic == "infrastructure"
            and n.sentiment == "positive"
            and n.published_on is not None
            and now.date() - timedelta(days=365) <= n.published_on <= now.date()
        }
    )
    values = {s.kind: momentum_score(s) for s in [*public, app] if s.usable}
    if observed:
        change = statistics.median(x.value for x in observed.values())
        values["observed_prices"] = min(100, max(0, change * 5))
    if area.section_status.get("classify_news") in ("ok", "empty"):
        values["infrastructure"] = min(100, infra_count * 50)
    coverage = sum(WEIGHTS[k] for k in values)
    score = sum(v * WEIGHTS[k] for k, v in values.items()) / coverage if coverage else None
    demand = any(qualified(s) for s in [*public, app] if s.kind != "locality_interest")
    attention = any(qualified(s) for s in public if s.kind == "locality_interest")
    corroborated = infra_count > 0 or any(x.value > 0 for x in observed.values())
    signal = (
        "corroborated_growth"
        if demand and corroborated
        else "interest_only"
        if demand or attention
        else "no_sustained_growth"
        if any(s.usable for s in [*public, app])
        else "insufficient_data"
    )
    recommendations = {
        "corroborated_growth": (
            "Prioritise further research: sustained property-related search "
            "interest is corroborated by observed prices or recent "
            "infrastructure reports. Development is not confirmed."
        ),
        "interest_only": (
            "Growing search attention warrants monitoring; evidence does not yet "
            "establish a developing area."
        ),
        "no_sustained_growth": (
            "No sustained, seasonally corroborated search growth found. "
            "Monitor rather than infer development."
        ),
        "insufficient_data": (
            "Insufficient search history to recommend this as a developing "
            "area. Keep collecting observations."
        ),
    }
    return AreaDevelopment(
        locality_key=area.locality_key,
        locality=area.locality,
        city=area.city,
        as_of=now,
        public_interest=public,
        app_interest=app,
        observed_price_growth=observed,
        recent_positive_infrastructure=infra_count,
        evidence_score=score,
        score_breakdown=values,
        coverage_pct=coverage,
        signal=signal,
        recommendation=recommendations[signal],
        limitations=[
            "Google Trends is sampled relative interest (0-100), not absolute search counts.",
            "App counts describe profiles, not verified people or the wider market.",
            "Searches and news do not prove construction, transactions, or causation.",
            "Thresholds/weights are transparent research heuristics, not a validated forecast.",
        ],
    )


def explain(ctx: PipelineContext, report: AreaDevelopment, area: AreaIntel) -> None:
    if not any(s.usable for s in [*report.public_interest, report.app_interest]):
        report.ai_review = "inconclusive"
        return
    news = [
        {
            "index": i,
            "title": n.title,
            "snippet": n.snippet,
            "published_on": n.published_on.isoformat() if n.published_on else None,
            "topic": n.topic,
            "sentiment": n.sentiment,
        }
        for i, n in enumerate(area.news)
    ]
    statistics_input = [
        {
            **s.model_dump(mode="json", exclude={"history", "source", "retrieved_at"}),
            "history": [p.model_dump(mode="json") for p in s.history[-65:]],
        }
        if s.usable
        else {
            "kind": s.kind,
            "query": s.query,
            "unit": s.unit,
            "usable": False,
            "note": "Insufficient usable history",
        }
        for s in [*report.public_interest, report.app_interest]
    ]
    try:
        review = ctx.llm.generate_structured(
            task="review_development",
            tier=ModelTier.REASONING,
            schema=DevelopmentReview,
            prompt=prompt_for(
                "review_development",
                locality=report.locality,
                signals=statistics_input,
                observed_prices={
                    k: v.model_dump(mode="json") for k, v in report.observed_price_growth.items()
                },
                computed_conclusion=report.signal,
                news=news,
            ),
        )
        selected, seen = [], set()
        for item in review.hypotheses:
            if item.news_index >= len(area.news):
                raise UpstreamError("Development explanation cites unknown news")
            article = area.news[item.news_index]
            if item.quote not in (article.title, article.snippet) or not item.quote.strip():
                raise UpstreamError(
                    "Development evidence must preserve a complete news title or snippet"
                )
            pattern, wording = DRIVERS[item.driver]
            if not re.search(pattern, item.quote, re.I):
                raise UpstreamError("Hypothesised driver is unsupported by its cited evidence")
            if (article.url, item.driver) in seen:
                continue
            seen.add((article.url, item.driver))
            selected.append(
                DevelopmentHypothesis(
                    driver=item.driver,
                    explanation=wording
                    + " This is a possible explanation, not demonstrated causation.",
                    evidence=Sourced(
                        value=item.quote,
                        confidence=min(item.confidence, 0.5),
                        method="llm",
                        sources=[article.source],
                        note="Unconfirmed causal hypothesis; news is not independent verification.",
                    ),
                )
            )
        report.ai_review, report.hypotheses = review.review, selected
    except AppError as exc:
        report.warnings.append(
            AreaIssue(
                section="review_development",
                provider="deepseek",
                code=exc.code,
                message=exc.message,
            )
        )


def rank_reports(reports: list[AreaDevelopment]) -> list[AreaDevelopment]:
    ordered = sorted(
        reports,
        key=lambda r: (r.signal != "corroborated_growth", -(r.evidence_score or 0), r.locality_key),
    )
    previous, rank = None, None
    for i, report in enumerate(ordered, 1):
        if report.signal == "corroborated_growth":
            if previous != report.evidence_score:
                rank = i
            report.rank, previous = rank, report.evidence_score
        else:
            report.rank = None
    return ordered


def build_report(
    ctx: PipelineContext,
    area: AreaIntel,
    public: list[SearchMomentum],
    *,
    now: datetime | None = None,
) -> AreaDevelopment:
    now = now or datetime.now(UTC)
    app = app_history(ctx.db, area.locality_key, now=now)
    report = assess(area, public, app, observed_growth(area), now=now)
    explain(ctx, report, area)
    return report
