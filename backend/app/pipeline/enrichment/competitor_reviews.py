"""F-06b: review-based hypotheses with bounded searches and exact quoted support.

The LLM selects complaint themes and evidence; code computes counts, confidence and text.
This sampled context never changes property scores or establishes a market-wide shortage.
"""

import math
import re
from enum import StrEnum
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.integrations.llm.base import ModelTier
from app.integrations.serpapi import engines
from app.pipeline.context import PipelineContext
from app.pipeline.verification import prompt_for
from app.schemas.area import AreaIssue
from app.schemas.common import SerpEngine
from app.schemas.competitor import Competitor, CompetitorReport, CompetitorReview
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef

MAX_REVIEWS = 8


class GapTheme(StrEnum):
    RESPONSE_TIME = "response_time"
    CUSTOMER_SUPPORT = "customer_support"
    PRICE_TRANSPARENCY = "price_transparency"
    SERVICE_QUALITY = "service_quality"
    FACILITIES = "facilities"
    ACCESSIBILITY = "accessibility"


THEMES = {
    GapTheme.RESPONSE_TIME: (
        "Faster responses or shorter waits",
        r"wait|slow|delay|response|respond",
    ),
    GapTheme.CUSTOMER_SUPPORT: (
        "More helpful customer support",
        r"support|customer|staff|rude|help|service|response|respond|ignor",
    ),
    GapTheme.PRICE_TRANSPARENCY: (
        "Clearer pricing and billing",
        r"price|cost|charg|bill|refund|payment|expensive",
    ),
    GapTheme.SERVICE_QUALITY: (
        "More reliable service delivery",
        r"quality|service|repair|broken|deliver|work|postpone|class|course",
    ),
    GapTheme.FACILITIES: (
        "Better facilities",
        r"clean|seating|toilet|bathroom|facility|facilities|space",
    ),
    GapTheme.ACCESSIBILITY: ("Easier access", r"park|access|wheelchair|entrance|location"),
}


class ReviewCitation(BaseModel):
    review_id: str
    quote: str = Field(min_length=8, max_length=160)


class GapCandidate(BaseModel):
    theme: GapTheme
    evidence: list[ReviewCitation] = Field(min_length=2, max_length=8)


class ReviewGapAnalysis(BaseModel):
    gaps: list[GapCandidate] = Field(default_factory=list, max_length=6)


def parse_reviews(data: dict, place: Competitor, search_id: str | None) -> list[CompetitorReview]:
    """Usable, de-duplicated first-page text; author information is excluded."""
    found = {}
    snippets = set()
    for row in data.get("reviews") or []:
        if not isinstance(row, dict):
            continue
        key, text, rating = row.get("review_id"), row.get("snippet"), row.get("rating")
        if not isinstance(key, str) or not key or not isinstance(text, str) or not text.strip():
            continue
        if isinstance(rating, bool) or not isinstance(rating, (int, float)):
            continue
        if not math.isfinite(rating) or not 1 <= rating <= 5:
            continue
        text = " ".join(text.split())[:800]
        if key in found or text.lower() in snippets:
            continue
        snippets.add(text.lower())
        link = row.get("link")
        if not isinstance(link, str) or urlparse(link).scheme not in {"https", "http"}:
            link = place.source.url
        found[key] = CompetitorReview(
            id=key,
            business=place.name,
            rating=rating,
            snippet=text,
            source=SourceRef(
                engine=SerpEngine.GOOGLE_MAPS_REVIEWS,
                url=link,
                title=f"Review of {place.name}",
                search_id=search_id,
            ),
        )
        if len(found) >= MAX_REVIEWS:
            break
    return list(found.values())


def grounded_gaps(
    analysis: ReviewGapAnalysis, reviews: list[CompetitorReview]
) -> list[Sourced[str]]:
    """At least two distinct low-rated reviews and exact, topic-relevant quotes per theme."""
    by_id = {review.id: review for review in reviews}
    found = {}
    for gap in analysis.gaps:
        supported = {}
        label, pattern = THEMES[gap.theme]
        for citation in gap.evidence:
            review = by_id.get(citation.review_id)
            if (
                review is not None
                and review.rating <= 3
                and citation.quote in review.snippet
                and re.search(pattern, citation.quote, re.I)
            ):
                supported[review.id] = (review, citation.quote)
        if len(supported) < 2 or gap.theme in found:
            continue
        businesses = sorted({review.business for review, _ in supported.values()})
        found[gap.theme] = Sourced(
            value=f"Potential gap: {label.lower()}. Supported by {len(supported)} "
            "sampled low-rated "
            f"reviews across {len(businesses)} business(es); confirm locally.",
            confidence=0.55,
            method=ExtractionMethod.LLM,
            sources=[review.source for review, _ in supported.values()],
            note="Sampled complaints, not a market-wide conclusion. "
            + " | ".join(f'{review.business}: "{quote}"' for review, quote in supported.values()),
        )
    return list(found.values())


def enrich_reviews(ctx: PipelineContext, report: CompetitorReport) -> None:
    report.review_places_limit = ctx.settings.competitor_review_max_places
    places = sorted(
        (p for p in report.competitors if p.data_id), key=lambda p: (-(p.reviews or 0), p.name)
    )[: report.review_places_limit]
    if not places:
        report.review_status = "unavailable" if report.competitors else "empty"
        return
    reviews = {}
    for place in places:
        try:
            response = ctx.serp.search(
                *engines.google_maps_reviews(place.data_id, ctx.settings, sort_by="ratingLow"),
                run_id=ctx.run_id,
            )
            report.review_places_sampled += 1
            for review in parse_reviews(response.data, place, response.search_id):
                reviews.setdefault(review.id, review)
        except AppError as exc:
            report.review_warnings.append(
                AreaIssue(
                    section="competitor_reviews",
                    provider="serpapi",
                    code=exc.code,
                    message=f"{place.name}: {exc.message}",
                )
            )
    report.reviews = list(reviews.values())
    if not reviews:
        report.review_status = "failed" if report.review_warnings else "empty"
        return
    report.review_status = "partial" if report.review_warnings else "ok"
    if sum(review.rating <= 3 for review in reviews.values()) < 2:
        return
    try:
        analysis = ctx.llm.generate_structured(
            task="competitor_gaps",
            schema=ReviewGapAnalysis,
            tier=ModelTier.REASONING,
            prompt=prompt_for(
                "competitor_gaps",
                business_type=report.business_type,
                reviews=[
                    review.model_dump(mode="json", exclude={"source"}) for review in report.reviews
                ],
            ),
        )
        report.gaps = grounded_gaps(analysis, report.reviews)
    except AppError as exc:
        report.review_status = "partial"
        report.review_warnings.append(
            AreaIssue(
                section="competitor_gaps",
                provider="llm",
                code=exc.code,
                message=exc.message,
            )
        )
