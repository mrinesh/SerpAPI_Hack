"""Historical interest: spike rejection, annual comparison, sparse data and query identity."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.errors import UpstreamError
from app.integrations.serpapi.engines import google_trends
from app.integrations.serpapi.gateway import SerpResponse
from app.pipeline.enrichment.search_history import parse_public, summarize
from app.schemas.development import InterestPoint, SearchMomentum


def history(values, kind="rental_interest"):
    return SearchMomentum(
        kind=kind,
        query="Whitefield rent",
        unit="relative_interest_0_100",
        history=[
            InterestPoint(week=date(2024, 1, 1) + timedelta(weeks=i), value=v)
            for i, v in enumerate(values)
        ],
        note="Measured test history",
    )


def test_sustained_growth_and_same_period_last_year():
    signal = summarize(history([20] * 52 + [40] * 13))
    assert signal.usable and signal.signal == "rising"
    assert signal.quarter_change_pct == 100
    assert signal.annual_change_pct == 100
    assert signal.sustained_weeks == 13


def test_one_spike_is_not_sustained_growth():
    signal = summarize(history([10] * 64 + [100]))
    assert signal.quarter_change_pct > 15
    assert signal.signal == "steady" and signal.sustained_weeks == 1


@pytest.mark.parametrize(
    "values,note",
    [([10] * 25, "26 complete"), ([0] * 65, "sparse"), ([0] * 52 + [50] * 13, "sparse")],
)
def test_missing_low_volume_or_zero_baseline_never_becomes_infinite_growth(values, note):
    result = summarize(history(values))
    assert not result.usable and result.quarter_change_pct is None and note in result.note


def test_falling_and_seasonal_surge_are_distinct():
    assert summarize(history([40] * 52 + [20] * 13)).signal == "falling"
    seasonal = summarize(history([40] * 13 + [20] * 39 + [40] * 13))
    assert seasonal.signal == "rising" and seasonal.annual_change_pct == 0


def test_gap_or_duplicate_week_is_unavailable():
    for duplicate in (False, True):
        series = history([30] * 65)
        series.history[15].week = (
            series.history[14].week if duplicate else series.history[15].week + timedelta(days=1)
        )
        assert not summarize(series).usable


def response(values, **overrides):
    timeline = [
        {
            "timestamp": str(int(datetime(2024, 1, 1, tzinfo=UTC).timestamp()) + i * 604800),
            "values": [{"query": "Whitefield", "extracted_value": v}],
        }
        for i, v in enumerate(values)
    ]
    return SerpResponse(
        "google_trends",
        {"q": "Whitefield", "geo": "IN-KA", "date": "today 5-y"},
        {
            "search_metadata": {"created_at": "2026-10-07"},
            "interest_over_time": {"timeline_data": timeline},
            **overrides,
        },
        "search-test",
        False,
    )


def test_parser_excludes_newest_bucket_and_carries_source_and_retrieval_date():
    result = parse_public(response([20] * 66), ["Whitefield"], "locality_interest")["Whitefield"]
    assert len(result.history) == 65 and result.usable
    assert result.source.search_id == "search-test" and result.retrieved_at == "2026-10-07"
    assert "date=today+5-y" in result.source.url


@pytest.mark.parametrize("value", [True, -1, 101, float("nan"), "50", None])
def test_invalid_provider_values_are_unavailable(value):
    result = parse_public(response([20] * 65 + [value]), ["Whitefield"], "locality_interest")[
        "Whitefield"
    ]
    assert not result.usable and "invalid" in result.note


def test_partial_bucket_query_mismatch_and_malformed_timeline():
    r = response([20] * 66)
    r.data["interest_over_time"]["timeline_data"][-2]["partial_data"] = True
    partial = parse_public(r, ["Whitefield"], "locality_interest")["Whitefield"]
    assert len(partial.history) == 64 and partial.annual_change_pct is None
    assert not parse_public(response([20] * 66), ["Koramangala"], "locality_interest")[
        "Koramangala"
    ].usable
    with pytest.raises(UpstreamError):
        parse_public(response([], interest_over_time=[]), ["Whitefield"], "locality_interest")


def test_query_limit_is_validated_not_silently_truncated():
    for queries in ([], ["a"] * 6, [""], ["a,b"]):
        with pytest.raises(ValueError):
            google_trends(queries)
    assert google_trends(["Whitefield", "Koramangala"])[1]["q"] == "Whitefield,Koramangala"
