from types import SimpleNamespace

import pytest

from app.core.errors import ReplayMiss, SearchBudgetExceeded
from app.pipeline.enrichment.competitor_reviews import (
    ReviewGapAnalysis,
    enrich_reviews,
    grounded_gaps,
    parse_reviews,
)
from app.schemas.competitor import Competitor, CompetitorReport
from app.schemas.provenance import SourceRef
from tests.unit.test_area import area_ctx
from tests.unit.test_competitors import CENTRE, NOW


def place(name="Test Cafe", data_id="0x1", reviews=20):
    return Competitor(
        name=name,
        category="Cafe",
        data_id=data_id,
        reviews=reviews,
        source=SourceRef(engine="google_maps", url="https://maps.google.com/test"),
    )


def rows():
    return {
        "reviews": [
            {
                "review_id": "a",
                "snippet": "We waited an hour for service",
                "rating": 1,
                "link": "https://maps.google.com/review/a",
            },
            {
                "review_id": "b",
                "snippet": "Very slow response to customers",
                "rating": 2,
                "link": "https://maps.google.com/review/b",
            },
        ]
    }


def analysis(**changes):
    gap = {
        "theme": "response_time",
        "evidence": [
            {"review_id": "a", "quote": "waited an hour"},
            {"review_id": "b", "quote": "slow response"},
        ],
    }
    gap.update(changes)
    return ReviewGapAnalysis.model_validate({"gaps": [gap]})


def report(places=None):
    return CompetitorReport(
        locality_key="bengaluru/koramangala",
        locality="Koramangala",
        business_type="Cafe",
        center=CENTRE,
        radius_km=2,
        competitors=places if places is not None else [place()],
        fetched_at=NOW,
        expires_at=NOW,
    )


def test_grounded_theme_has_exact_sources_and_code_counts():
    reviews = parse_reviews(rows(), place(), "s-1")
    [gap] = grounded_gaps(analysis(), reviews)
    assert "2 sampled" in gap.value and "1 business" in gap.value
    assert gap.confidence == 0.55 and len(gap.sources) == 2
    assert gap.sources[0].engine == "google_maps_reviews"
    assert "waited an hour" in gap.note and "confirm locally" in gap.value


@pytest.mark.parametrize(
    "citations",
    [
        [
            {"review_id": "invented", "quote": "waited an hour"},
            {"review_id": "b", "quote": "slow response"},
        ],
        [
            {"review_id": "a", "quote": "waited two hours"},
            {"review_id": "b", "quote": "slow response"},
        ],
        [
            {"review_id": "a", "quote": "waited an hour"},
            {"review_id": "a", "quote": "waited an hour"},
        ],
    ],
)
def test_invented_evidence_and_duplicate_citations_cannot_create_a_gap(citations):
    assert grounded_gaps(analysis(evidence=citations), parse_reviews(rows(), place(), "s")) == []


def test_high_ratings_and_wrong_theme_are_not_support():
    reviews = parse_reviews(rows(), place(), "s")
    assert grounded_gaps(analysis(theme="facilities"), reviews) == []
    reviews[0].rating = 5
    assert grounded_gaps(analysis(), reviews) == []


def test_parser_skips_malformed_duplicate_and_empty_reviews_and_bounds_text():
    data = rows()
    data["reviews"] += [
        data["reviews"][0],
        None,
        {"review_id": "bad", "snippet": "x", "rating": float("nan")},
        {"review_id": "empty", "snippet": " ", "rating": 1},
        {"review_id": "long", "snippet": "x" * 1000, "rating": 3},
    ]
    reviews = parse_reviews(data, place(), "s")
    assert [r.id for r in reviews] == ["a", "b", "long"]
    assert len(reviews[-1].snippet) == 800


def test_enrichment_bounds_calls_and_sends_no_author_or_url_to_model(db):
    ctx = area_ctx(db)
    calls = []
    prompts = []

    class Serp:
        def search(self, engine, params, **kwargs):
            calls.append((engine, params))
            return SimpleNamespace(data=rows(), search_id="s")

    class LLM:
        def generate_structured(self, **kwargs):
            prompts.append(kwargs["prompt"])
            return analysis()

    ctx.serp, ctx.llm = Serp(), LLM()
    data = report(
        [
            place("Low", reviews=3),
            place("High", "0x2", reviews=100),
            place("Middle", "0x3", reviews=50),
        ]
    )
    enrich_reviews(ctx, data)
    assert len(calls) == 1 and calls[0][1]["data_id"] == "0x2"
    assert calls[0][1]["sort_by"] == "ratingLow"
    assert data.review_status == "ok" and data.gaps and data.review_places_sampled == 1
    assert "https://" not in prompts[0] and '"user"' not in prompts[0]


@pytest.mark.parametrize("failure", [ReplayMiss("missing"), SearchBudgetExceeded("cap")])
def test_provider_or_budget_failure_is_visible_without_failing_report(db, failure):
    ctx = area_ctx(db)

    class Serp:
        def search(self, *args, **kwargs):
            raise failure

    ctx.serp = Serp()
    data = report()
    enrich_reviews(ctx, data)
    assert data.status == "ok" and data.review_status == "failed"
    assert data.review_warnings[0].code == failure.code


def test_no_review_ids_means_no_calls(db):
    data = report([place(data_id=None)])
    enrich_reviews(area_ctx(db), data)
    assert data.review_status == "unavailable" and data.gaps == []


def test_bad_review_link_falls_back_to_business_source_and_sample_is_bounded():
    data = {
        "reviews": [
            {
                "review_id": str(i),
                "snippet": f"Complaint number {i}",
                "rating": 2,
                "link": "javascript:alert(1)",
            }
            for i in range(20)
        ]
    }
    reviews = parse_reviews(data, place(), "s")
    assert len(reviews) == 8
    assert all(r.source.url == place().source.url for r in reviews)


def test_llm_replay_miss_retains_reviews_as_partial(db):
    ctx = area_ctx(db)

    class Serp:
        def search(self, *args, **kwargs):
            return SimpleNamespace(data=rows(), search_id="s")

    class LLM:
        def generate_structured(self, **kwargs):
            raise ReplayMiss("No recorded analysis")

    ctx.serp, ctx.llm = Serp(), LLM()
    data = report()
    enrich_reviews(ctx, data)
    assert data.review_status == "partial" and len(data.reviews) == 2
    assert data.review_warnings[0].provider == "llm"
