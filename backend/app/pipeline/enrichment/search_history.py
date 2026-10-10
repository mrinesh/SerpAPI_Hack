"""Public Google Trends history and the app's own search history for developing-area signals
(ADR 0025). Ported from gscode007's `feature/search-driven-area-insights` branch onto main's
area intelligence. All arithmetic is in code; no AI is involved here."""

import math
import statistics
from datetime import UTC, date, datetime, timedelta
from itertools import pairwise
from urllib.parse import urlencode

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, UpstreamError
from app.db.models import SearchIntentRow
from app.integrations.serpapi import engines
from app.integrations.serpapi.gateway import SerpResponse
from app.pipeline.context import PipelineContext
from app.pipeline.enrichment.area import locality_key
from app.reference import Market
from app.schemas.area import AreaIssue
from app.schemas.common import SerpEngine
from app.schemas.development import InterestPoint, SearchMomentum
from app.schemas.profile import InvestorProfile
from app.schemas.provenance import SourceRef
from app.services.access import profile_ids

WINDOW_WEEKS = 13


def as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; they are stored in UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def record_intent(db: Session, run_id: str, profile: InvestorProfile, market: Market) -> None:
    """One row per requested locality, keyed like the area it will produce."""
    for slug in profile.localities:
        place = market.locality(slug)
        db.add(
            SearchIntentRow(
                run_id=run_id,
                profile_id=profile.id,
                locality_key=locality_key(place.name if place else slug, market.city),
            )
        )


def summarize(momentum: SearchMomentum, *, public: bool = True) -> SearchMomentum:
    """Last 13 complete weeks vs previous 13, plus the same 13 weeks 52 weeks earlier."""
    points = momentum.history
    if len(points) < 26:
        momentum.note += "; need at least 26 complete weekly observations"
        return momentum
    recent = points[-26:]
    if any((b.week - a.week).days != 7 for a, b in pairwise(points)):
        momentum.note += "; weekly dates are missing or irregular"
        return momentum
    if public and sum(p.value > 0 for p in recent) < 20:
        momentum.note += "; sparse/low-volume relative interest cannot support a growth claim"
        return momentum
    if not public and (momentum.sample_size or 0) < 5:
        momentum.note += "; fewer than five distinct profiles: insufficient app sample"
        return momentum
    previous, latest = recent[:13], recent[13:]
    base = statistics.mean(p.value for p in previous)
    current = statistics.mean(p.value for p in latest)
    momentum.previous_mean, momentum.recent_mean = base, current
    if base <= 0:
        momentum.note += "; zero baseline: percentage growth cannot be estimated"
        return momentum
    change = (current / base - 1) * 100
    momentum.quarter_change_pct = change
    momentum.sustained_weeks = sum(p.value > base for p in latest)
    if len(points) >= 65:
        annual_base = statistics.mean(p.value for p in points[-65:-52])
        if annual_base > 0:
            momentum.annual_change_pct = (current / annual_base - 1) * 100
    momentum.usable = True
    momentum.signal = (
        "rising"
        if change >= 15 and momentum.sustained_weeks >= 8
        else "falling"
        if change <= -15 and sum(p.value < base for p in latest) >= 8
        else "steady"
    )
    return momentum


def parse_public(
    response: SerpResponse, queries: list[str], kind: str
) -> dict[str, SearchMomentum]:
    interest = response.data.get("interest_over_time", {})
    if not isinstance(interest, dict):
        raise UpstreamError("Malformed Google Trends interest data")
    timeline = interest.get("timeline_data", [])
    if not isinstance(timeline, list):
        raise UpstreamError("Malformed Google Trends timeline")
    params = response.params
    source = SourceRef(
        engine=SerpEngine.GOOGLE_TRENDS,
        search_id=response.search_id,
        title="Google Trends relative interest history",
        url="https://trends.google.com/trends/explore?"
        + urlencode(
            {"q": params.get("q", ""), "geo": params.get("geo", ""), "date": params.get("date", "")}
        ),
    )
    metadata = response.data.get("search_metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    output = {}
    for query in queries:
        points = []
        invalid = False
        for row in timeline:
            try:
                stamp = int(row["timestamp"])
                week = datetime.fromtimestamp(stamp, UTC).date()
                entries = [v for v in row["values"] if v.get("query") == query]
                if len(entries) != 1:
                    invalid = True
                    break
                entry = entries[0]
                value = entry.get("extracted_value")
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or not 0 <= value <= 100
                ):
                    invalid = True
                    break
                points.append(
                    (
                        week,
                        float(value),
                        bool(
                            row.get("partial_data")
                            or row.get("is_partial")
                            or entry.get("partial_data")
                        ),
                    )
                )
            except (KeyError, ValueError, TypeError, AttributeError, OverflowError, OSError):
                invalid = True
                break
        points.sort()
        # Always exclude the newest bucket as a conservative incomplete-period guard.
        complete = [InterestPoint(week=w, value=v) for w, v, partial in points[:-1] if not partial]
        momentum = SearchMomentum(
            kind=kind,
            query=query,
            unit="relative_interest_0_100",
            geo=params.get("geo"),
            history=[] if invalid else complete[-104:],
            source=source,
            retrieved_at=metadata.get("created_at"),
            note=(
                "Relative Google search interest, not search counts or proof of development; "
                "newest bucket excluded"
            )
            + ("; invalid or mismatched provider data" if invalid else ""),
        )
        output[query] = summarize(momentum)
    return output


def public_history(
    ctx: PipelineContext, market: Market, slugs: list[str]
) -> tuple[dict[str, list[SearchMomentum]], list[AreaIssue]]:
    output = {slug: [] for slug in slugs}
    issues = []
    for kind, suffix in (("locality_interest", ""), ("rental_interest", " rent")):
        mapping = {slug: market.locality(slug).name + suffix for slug in slugs}
        queries = list(mapping.values())
        if not queries:
            continue
        try:
            response = ctx.serp.search(
                *engines.google_trends(queries, geo=market.trends_geo, date="today 5-y"),
                run_id=ctx.run_id,
            )
            parsed = parse_public(response, queries, kind)
        except AppError as exc:
            issues.append(
                AreaIssue(
                    section=f"trends:{kind}",
                    provider="serpapi",
                    code=exc.code,
                    message=exc.message,
                )
            )
            parsed = {
                q: SearchMomentum(
                    kind=kind,
                    query=q,
                    unit="relative_interest_0_100",
                    geo=market.trends_geo,
                    note=f"{exc.code}: {exc.message}",
                )
                for q in queries
            }
        for slug, query in mapping.items():
            output[slug].append(parsed[query])
    return output, issues


def app_history(db: Session, key: str, *, now: datetime) -> SearchMomentum:
    earliest = db.scalar(
        select(func.min(SearchIntentRow.created_at)).where(
            SearchIntentRow.profile_id.in_(profile_ids(db))
        )
    )
    momentum = SearchMomentum(
        kind="app_searches",
        query=key,
        unit="distinct_profiles_per_week",
        note=(
            "Actual app search intents; one profile counted once per locality/week. "
            "Profiles are not verified people"
        ),
    )
    if earliest is None:
        return summarize(momentum, public=False)
    beginning = as_utc(earliest).date()
    # Skip the first collection week and the current week, both potentially partial.
    start = beginning - timedelta(days=beginning.weekday()) + timedelta(days=7)
    today = as_utc(now).date()
    end = today - timedelta(days=today.weekday())
    start = max(start, end - timedelta(weeks=104))
    rows = db.execute(
        select(SearchIntentRow.created_at, SearchIntentRow.profile_id).where(
            SearchIntentRow.locality_key == key,
            SearchIntentRow.profile_id.in_(profile_ids(db)),
            SearchIntentRow.created_at >= datetime.combine(start, datetime.min.time(), UTC),
            SearchIntentRow.created_at < datetime.combine(end, datetime.min.time(), UTC),
        )
    ).all()
    grouped: dict[date, set[str]] = {}
    for when, profile in rows:
        day = as_utc(when).date()
        week = day - timedelta(days=day.weekday())
        grouped.setdefault(week, set()).add(profile)
    profiles = set()
    current = start
    while current < end:
        ids = grouped.get(current, set())
        momentum.history.append(InterestPoint(week=current, value=len(ids)))
        if current >= end - timedelta(weeks=26):
            profiles.update(ids)
        current += timedelta(weeks=1)
    momentum.sample_size = len(profiles)
    return summarize(momentum, public=False)
