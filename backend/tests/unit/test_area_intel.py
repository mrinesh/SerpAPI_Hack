"""F-05 contract tests: normalization, evidence, partial failures and cache boundaries."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.config import ProviderMode, Settings
from app.core.errors import InvalidInput, ReplayMiss, UpstreamError
from app.db.models import AreaIntelRow
from app.integrations.serpapi.gateway import SerpResponse
from app.pipeline.enrichment.area import get_area_intel, locality_key
from app.pipeline.enrichment.area_sources import (
    distance_km,
    normalize_amenities,
    normalize_news,
    resolve_locality,
)
from app.schemas.area import AmenityCategory
from app.schemas.common import GeoPoint, SerpEngine
from app.schemas.provenance import ExtractionMethod, Sourced
from app.services.properties import get_area

NOW = datetime(2026, 10, 6, tzinfo=UTC)
POINT = GeoPoint(lat=12.97, lng=77.75)
STORY = {
    "title": "Whitefield metro extension planned",
    "link": "https://example.org/metro",
    "snippet": "Whitefield metro extension is planned, not completed.",
    "source": {"name": "Test publication"},
    "iso_date": "2026-10-05T10:00:00Z",
}


def response(data, engine=SerpEngine.GOOGLE_MAPS, params=None):
    return SerpResponse(engine, params or {"q": "Whitefield"}, data, "search-test", False)


class AreaLLM:
    def __init__(self, quote=None, fail=None, classifications=None):
        self.calls, self.quote, self.fail, self.classifications = [], quote, fail, classifications

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs["task"])
        if kwargs["task"] == self.fail:
            raise UpstreamError("LLM test failure")
        inputs = json.loads(kwargs["prompt"].split("INPUT JSON:\n")[1])
        items = inputs["news_items"]
        if kwargs["task"] == "classify_news":
            return kwargs["schema"].model_validate(
                {
                    "items": self.classifications
                    if self.classifications is not None
                    else [
                        {"index": i, "topic": "infrastructure", "sentiment": "neutral"}
                        for i in range(len(items))
                    ]
                }
            )
        return kwargs["schema"].model_validate(
            {
                "facts": [
                    {
                        "news_index": 0,
                        "quote": self.quote or items[0]["title"],
                    }
                ]
            }
        )


class AreaSerp:
    def __init__(self, fail=None, news=None, center=True, malformed=None):
        self.calls, self.fail, self.news = [], fail, news
        self.center, self.malformed = center, malformed

    def search(self, engine, params, run_id=None):
        self.calls.append((engine, params, run_id))
        if self.fail and self.fail in params["q"]:
            raise ReplayMiss("Missing test fixture")
        if self.malformed and self.malformed in params["q"]:
            return response({"local_results": "broken"}, engine, params)
        if engine == SerpEngine.GOOGLE_NEWS:
            return response(
                {"news_results": [STORY] if self.news is None else self.news}, engine, params
            )
        if params["q"] == "Whitefield, Bengaluru":
            return response(
                {
                    "place_results": {
                        "title": "Whitefield" if self.center else "Whitefield Clinic",
                        "gps_coordinates": {"latitude": POINT.lat, "longitude": POINT.lng},
                    }
                },
                engine,
                params,
            )
        return response(
            {
                "local_results": [
                    {
                        "title": "Whitefield Test Amenity",
                        "type": "Subway station"
                        if "metro" in params["q"]
                        else "School"
                        if "school" in params["q"]
                        else "Hospital",
                        "place_id": "test-place",
                        "address": "Whitefield, Bengaluru",
                        "rating": 4.2,
                        "reviews": 100,
                        "gps_coordinates": {"latitude": 12.971, "longitude": 77.751},
                    }
                ]
            },
            engine,
            params,
        )


def context(db, serp=None, llm=None):
    return SimpleNamespace(
        db=db,
        run_id="run-test",
        profile=SimpleNamespace(city="Bengaluru"),
        settings=Settings(_env_file=None),
        serp=serp or AreaSerp(),
        llm=llm or AreaLLM(),
    )


@pytest.mark.parametrize(
    ("locality", "city", "key"),
    [
        (" WHITEFIELD ", " Bengaluru ", "bengaluru/whitefield"),
        ("HSR   Layout", "bangalore", "bengaluru/hsr-layout"),
        ("hsr-layout", "Bengaluru", "bengaluru/hsr-layout"),
        ("Krishnarajapuram", "Bengaluru", "bengaluru/kr-puram"),
    ],
)
def test_locality_normalization(locality, city, key):
    assert locality_key(locality, city) == key


@pytest.mark.parametrize(
    ("locality", "city"), [("Fake Area", "Bengaluru"), ("Whitefield", "Delhi")]
)
def test_unknown_geography_is_rejected(locality, city):
    with pytest.raises(InvalidInput):
        locality_key(locality, city)


def test_miss_hit_expiry_and_price_levels_are_run_specific(db):
    ctx = context(db)
    level = Sourced[float](value=8000, confidence=0.8, method=ExtractionMethod.REGEX)
    first = get_area_intel(ctx, "whitefield", now=NOW, benchmarks={"apartment": level})
    assert not first.cache_hit and first.price_levels["apartment"].value == 8000
    assert len(ctx.serp.calls) == 5
    assert all(call[2] == "run-test" for call in ctx.serp.calls)
    second = get_area_intel(ctx, " WHITEFIELD ", now=NOW + timedelta(hours=1))
    assert second.cache_hit and second.price_levels == {} and len(ctx.serp.calls) == 5
    third = get_area_intel(ctx, "whitefield", now=NOW + timedelta(hours=168))
    assert not third.cache_hit and len(ctx.serp.calls) == 10


def test_record_mode_does_not_skip_raw_recordings(db):
    ctx = context(db)
    get_area_intel(ctx, "whitefield", now=NOW)
    ctx.settings.serpapi_mode = ProviderMode.RECORD
    get_area_intel(ctx, "whitefield", now=NOW)
    assert len(ctx.serp.calls) == 10


def test_cache_mode_change_and_corruption_trigger_rebuild(db, caplog):
    ctx = context(db)
    get_area_intel(ctx, "whitefield", now=NOW)
    ctx.settings.llm_mode = ProviderMode.LIVE
    assert not get_area_intel(ctx, "whitefield", now=NOW).cache_hit
    row = db.get(AreaIntelRow, "bengaluru/whitefield")
    row.data = {"corrupt": True}
    db.commit()
    assert not get_area_intel(ctx, "whitefield", now=NOW).cache_hit
    assert "area cache invalid locality=bengaluru/whitefield" in caplog.text


def test_source_metadata_and_infrastructure_remain_tied_to_original_evidence(db):
    area = get_area_intel(context(db), "whitefield", now=NOW)
    assert area.news[0].outlet == "Test publication"
    assert area.news[0].published_on.isoformat() == "2026-10-05"
    fact = area.infrastructure[0].evidence
    assert fact.value == STORY["title"] and fact.sources == [area.news[0].source]
    assert fact.sources[0].search_id == "search-test"
    assert area.center_source.search_id == "search-test"
    assert area.infrastructure_summary.sources == fact.sources
    assert not area.warnings


@pytest.mark.parametrize(
    "quote", ["Whitefield metro is completed", " ", "Whitefield metro extension"]
)
def test_invented_infrastructure_is_rejected_and_not_cached_as_complete(db, quote):
    ctx = context(db, llm=AreaLLM(quote=quote))
    area = get_area_intel(ctx, "whitefield", now=NOW)
    assert not area.infrastructure and area.infrastructure_summary is None
    assert area.section_status["summarize_area"] == "failed"
    assert area.warnings[0].code == "upstream_error" and area.expires_at == NOW
    get_area_intel(ctx, "whitefield", now=NOW + timedelta(seconds=1))
    assert len(ctx.serp.calls) == 10


def test_bad_classification_indices_and_llm_failure_leave_raw_news(db):
    for llm in (AreaLLM(classifications=[]), AreaLLM(fail="classify_news")):
        area = get_area_intel(context(db, llm=llm), "whitefield", now=NOW)
        assert area.news and not area.infrastructure
        assert area.section_status["classify_news"] == "failed"


def test_provider_failure_preserves_other_sections_and_emits_context(db, caplog):
    area = get_area_intel(context(db, serp=AreaSerp(fail="hospital")), "whitefield", now=NOW)
    assert len(area.amenities) == 2 and area.news
    assert area.section_status["amenities:hospital"] == "failed"
    assert area.warnings[0].code == "replay_miss"
    assert "locality=bengaluru/whitefield operation=amenities:hospital" in caplog.text


def test_malformed_section_is_distinguished_from_successful_empty_section(db):
    area = get_area_intel(
        context(db, serp=AreaSerp(malformed="school", news=[])), "whitefield", now=NOW
    )
    assert area.section_status["amenities:school"] == "failed"
    assert area.section_status["news"] == "empty"
    assert area.warnings[0].code == "upstream_error"


def test_ambiguous_geocode_never_invents_center_or_distances(db):
    area = get_area_intel(context(db, serp=AreaSerp(center=False)), "whitefield", now=NOW)
    assert area.center is None and all(a.distance_km is None for a in area.amenities)
    assert area.section_status["center"] == "unavailable"


def test_empty_news_does_not_call_llm(db):
    ctx = context(db, serp=AreaSerp(news=[]))
    area = get_area_intel(ctx, "whitefield", now=NOW)
    assert not area.news and not area.infrastructure and not ctx.llm.calls
    assert not area.warnings and area.expires_at > NOW


def test_amenities_deduplicate_filter_distant_places_and_preserve_coordinates():
    place = resolve_locality("whitefield", "Bengaluru")[1]
    row = {
        "title": "Test school",
        "type": "School",
        "place_id": "a",
        "rating": 4.5,
        "gps_coordinates": {"latitude": 12.97, "longitude": 77.75},
    }
    far = dict(row, place_id="far", gps_coordinates={"latitude": 10, "longitude": 70})
    found = normalize_amenities(
        response({"local_results": [row, row, far]}), AmenityCategory.SCHOOL, POINT, place
    )
    assert len(found) == 1 and found[0].location == POINT and found[0].distance_km == 0
    assert found[0].source.search_id == "search-test"
    assert distance_km(POINT, GeoPoint(lat=13.97, lng=77.75)) == pytest.approx(111.20, abs=0.01)


def test_news_flattening_deduplication_alias_matching_and_unrelated_filter():
    place = resolve_locality("whitefield", "Bengaluru")[1]
    unrelated = dict(STORY, title="Bengaluru metro expansion", snippet="Citywide development")
    data = {"news_results": [{"stories": [STORY, STORY], "highlight": STORY}, unrelated]}
    found = normalize_news(response(data, SerpEngine.GOOGLE_NEWS), place)
    assert len(found) == 1 and found[0].url == STORY["link"]
    false_match = dict(STORY, title="Whitefieldshire metro", snippet=None)
    assert (
        normalize_news(response({"news_results": [false_match]}, SerpEngine.GOOGLE_NEWS), place)
        == []
    )


@pytest.mark.parametrize(
    "data",
    [
        {"news_results": {}},
        {"news_results": [3]},
        {"news_results": [dict(STORY, iso_date="bad date")]},
        {"news_results": [dict(STORY, link="javascript:alert(1)")]},
    ],
)
def test_malformed_news_never_silently_corrupts_payload(data):
    with pytest.raises(UpstreamError):
        normalize_news(
            response(data, SerpEngine.GOOGLE_NEWS), resolve_locality("whitefield", "Bengaluru")[1]
        )


def test_amenity_category_comes_from_place_types_not_business_name():
    place = resolve_locality("whitefield", "Bengaluru")[1]
    station = {
        "title": "Sri Sathya Sai Hospital",
        "type": "Subway station",
        "gps_coordinates": {"latitude": POINT.lat, "longitude": POINT.lng},
    }
    raw = response({"local_results": [station]})
    assert normalize_amenities(raw, AmenityCategory.METRO, POINT, place)[0].category == "metro"
    assert normalize_amenities(raw, AmenityCategory.HOSPITAL, POINT, place) == []


def test_internal_errors_are_not_swallowed_as_provider_warnings(db):
    class BrokenSerp(AreaSerp):
        def search(self, *_args, **_kwargs):
            raise RuntimeError("Internal bug")

    with pytest.raises(RuntimeError, match="Internal bug"):
        get_area_intel(context(db, serp=BrokenSerp()), "whitefield", now=NOW)


def test_read_only_service_marks_expired_data_stale_and_rejects_corruption(db):
    get_area_intel(context(db), "whitefield", now=NOW - timedelta(days=10))
    assert get_area(db, "bangalore/WHITEFIELD").stale
    row = db.get(AreaIntelRow, "bengaluru/whitefield")
    row.data = {}
    db.commit()
    from app.core.errors import AppError

    with pytest.raises(AppError, match="Invalid area cache"):
        get_area(db, "bengaluru/whitefield")
