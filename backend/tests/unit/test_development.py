"""Recommendations require measured demand and corroboration; AI cannot change the result."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.pipeline.enrichment.development import DevelopmentReview, assess, explain, rank_reports
from app.schemas.area import AreaIntel, InfrastructureFact, NewsItem
from app.schemas.development import SearchMomentum
from app.schemas.provenance import Sourced, SourceRef

NOW = datetime(2026, 10, 7, tzinfo=UTC)
SOURCE = SourceRef(engine="google_news", url="https://example.org/metro")


def signal(kind="rental_interest", **kwargs):
    return SearchMomentum(
        kind=kind,
        query="Whitefield",
        unit="relative_interest_0_100",
        usable=True,
        signal="rising",
        quarter_change_pct=30,
        annual_change_pct=20,
        note="Measured history",
        **kwargs,
    )


def empty_app():
    return SearchMomentum(
        kind="app_searches",
        query="bengaluru/whitefield",
        unit="distinct_profiles_per_week",
        note="No app baseline",
    )


def area(**kwargs):
    return AreaIntel(
        locality_key="bengaluru/whitefield",
        locality="Whitefield",
        city="Bengaluru",
        fetched_at=NOW,
        expires_at=NOW + timedelta(days=1),
        **kwargs,
    )


def price(method="regex", value=10):
    return {
        "apartment": Sourced(
            value=value,
            confidence=0.8,
            method=method,
            sources=[SourceRef(engine="google", url="https://example.org/rates")],
        )
    }


def test_demand_and_observed_corroboration_required():
    growth = signal()
    assert assess(area(), [growth], empty_app(), price(), now=NOW).signal == "corroborated_growth"
    assert assess(area(), [growth], empty_app(), {}, now=NOW).signal == "interest_only"
    assert (
        assess(area(), [signal("locality_interest")], empty_app(), price(), now=NOW).signal
        == "interest_only"
    )
    report = assess(area(), [growth], empty_app(), price("query"), now=NOW)
    assert report.signal == "interest_only" and not report.observed_price_growth


@pytest.mark.parametrize("annual", [None, 0, 9.9, -10])
def test_missing_annual_or_recurring_seasonality_does_not_receive_rank(annual):
    growth = signal().model_copy(update={"annual_change_pct": annual})
    report = assess(area(), [growth], empty_app(), price(), now=NOW)
    assert report.signal == "no_sustained_growth"
    assert rank_reports([report])[0].rank is None


def test_app_demand_can_qualify_independently_of_public_interest():
    app = signal("app_searches").model_copy(update={"unit": "distinct_profiles_per_week"})
    assert assess(area(), [], app, price(), now=NOW).signal == "corroborated_growth"
    assert assess(area(), [], empty_app(), price(), now=NOW).signal == "insufficient_data"


def test_news_is_dated_positive_and_deduplicated_not_completion_proof():
    story = NewsItem(
        title="Metro extension proposed",
        url=SOURCE.url,
        source=SOURCE,
        published_on=NOW.date(),
        topic="infrastructure",
        sentiment="positive",
    )
    fact = InfrastructureFact(
        topic="infrastructure", evidence=Sourced(value=story.title, method="llm", sources=[SOURCE])
    )
    report = assess(
        area(
            news=[story, story], infrastructure=[fact, fact], section_status={"classify_news": "ok"}
        ),
        [signal()],
        empty_app(),
        {},
        now=NOW,
    )
    assert report.recent_positive_infrastructure == 1
    assert report.signal == "corroborated_growth" and "not confirmed" in report.recommendation
    for changes in (
        {"sentiment": "negative"},
        {"published_on": None},
        {"published_on": (NOW - timedelta(days=366)).date()},
        {"published_on": (NOW + timedelta(days=1)).date()},
    ):
        report = assess(
            area(news=[story.model_copy(update=changes)], infrastructure=[fact]),
            [signal()],
            empty_app(),
            {},
            now=NOW,
        )
        assert report.recent_positive_infrastructure == 0 and report.signal == "interest_only"


def test_ranks_are_deterministic_with_shared_rank_for_ties():
    first = assess(area(), [signal()], empty_app(), price(), now=NOW)
    second = first.model_copy(update={"locality_key": "bengaluru/aaa"})
    no_demand = assess(area(), [], empty_app(), price(value=100), now=NOW)
    ordered = rank_reports([first, no_demand, second])
    assert ordered[:2] == [second, first]
    assert [r.rank for r in ordered] == [1, 1, None]


class ReviewLLM:
    def __init__(self, quote, driver="transport", index=0):
        self.quote, self.driver, self.index = quote, driver, index

    def generate_structured(self, **kwargs):
        return DevelopmentReview(
            review="mixed",
            hypotheses=[
                dict(driver=self.driver, news_index=self.index, quote=self.quote, confidence=0.95)
            ],
        )


def test_cited_ai_hypothesis_keeps_qualifiers_and_cannot_change_score():
    title = "Metro extension proposed, funding pending"
    intel = area(news=[NewsItem(title=title, url=SOURCE.url, source=SOURCE)])
    report = assess(intel, [signal()], empty_app(), price(), now=NOW)
    original = (report.signal, report.evidence_score, report.score_breakdown.copy())
    explain(SimpleNamespace(llm=ReviewLLM(title)), report, intel)
    assert report.ai_review == "mixed" and not report.warnings
    assert report.hypotheses[0].evidence.value == title
    assert report.hypotheses[0].evidence.confidence == 0.5
    assert "not demonstrated causation" in report.hypotheses[0].explanation
    assert (report.signal, report.evidence_score, report.score_breakdown) == original


@pytest.mark.parametrize(
    "quote,driver,index",
    [
        ("Invented office opening", "employment", 0),
        ("Metro planned", "employment", 0),
        ("Metro planned", "transport", 9),
    ],
)
def test_ai_invented_quotes_unsupported_drivers_and_indices_are_withheld(quote, driver, index):
    intel = area(news=[NewsItem(title="Metro planned", url=SOURCE.url, source=SOURCE)])
    report = assess(intel, [signal()], empty_app(), price(), now=NOW)
    explain(SimpleNamespace(llm=ReviewLLM(quote, driver, index)), report, intel)
    assert report.ai_review == "unavailable" and not report.hypotheses
    assert report.warnings and report.signal == "corroborated_growth"
