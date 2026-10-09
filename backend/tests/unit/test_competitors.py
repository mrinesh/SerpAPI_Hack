"""Competitor analysis: parsing, figures, readings, cache and failures (F-06, ADR 0023)."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.db.models import CompetitorReportRow
from app.pipeline.enrichment.competitors import (
    density_level,
    fill_figures,
    get_competitor_report,
    parse_competitors,
    readings_for,
    report_key,
)
from app.schemas.area import AreaIntel
from app.schemas.common import GeoPoint, Level
from app.schemas.competitor import Competitor, CompetitorReport
from app.schemas.provenance import SourceRef
from tests.unit.test_area import NoSerp, area_ctx

CENTRE = GeoPoint(lat=12.9352403, lng=77.624532)  # Koramangala, as geocoded in F-05
NOW = datetime.now(UTC)
FIXTURE = Path(__file__).parents[2] / "fixtures/serpapi/google_maps/0faa47e764f1b253ec049680.json"


def place(title, lat, lng=77.624532, place_id=None, **extra):
    return {
        "title": title,
        "type": "Software company",
        "gps_coordinates": {"latitude": lat, "longitude": lng},
        "place_id": place_id,
        **extra,
    }


def area(center=CENTRE):
    return AreaIntel(
        locality_key="bengaluru/koramangala",
        locality="Koramangala",
        city="Bengaluru",
        center=center,
        fetched_at=NOW,
        expires_at=NOW,
    )


def test_places_are_kept_within_the_radius_once_each_nearest_first():
    data = {
        "local_results": [
            place("Far Co", 12.97, place_id="far"),  # ~3.9 km
            place("Mid Co", 12.945, place_id="mid", rating=4.5, reviews=20, data_id="0x1"),
            place("Near Co", 12.936, place_id="near"),
            place("Near Co again", 12.936, place_id="near"),  # same place
            {"title": "No position"},
            place("", 12.936),
        ]
    }
    found = parse_competitors(data, CENTRE, "s-1")
    assert [(c.name, c.distance_km) for c in found] == [("Near Co", 0.08), ("Mid Co", 1.09)]
    assert found[1].category == "Software company" and found[1].data_id == "0x1"
    assert found[1].source.search_id == "s-1"


def test_recorded_koramangala_search_has_seven_places_within_two_km():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))["response"]
    found = parse_competitors(data, CENTRE, "s-1")
    assert len(data["local_results"]) == 20
    assert len(found) == 7
    assert found[0].name == "Z IT Support & Services" and found[0].distance_km == 0.3
    assert all(c.distance_km <= 2.0 for c in found)


@pytest.mark.parametrize(
    ("count", "level"), [(0, Level.LOW), (3, Level.LOW), (4, Level.MEDIUM), (9, Level.MEDIUM),
                         (10, Level.HIGH), (20, Level.HIGH)],
)  # fmt: skip
def test_density_level_bands(count, level):
    assert density_level(count) == level


def test_figures_average_only_rated_places_and_sum_reviews():
    def competitor(rating, reviews):
        return Competitor(name="x", category="", rating=rating, reviews=reviews,
                          source=SourceRef(engine="google_maps"))  # fmt: skip

    report = CompetitorReport(
        locality_key="k", locality="K", business_type="cafe", center=CENTRE, radius_km=2.0,
        competitors=[competitor(4.0, 10), competitor(5.0, None), competitor(None, 5)] * 2,
        fetched_at=NOW, expires_at=NOW,
    )  # fmt: skip
    fill_figures(report)
    assert report.avg_rating == 4.5
    assert report.total_reviews == 30
    assert report.density_per_sq_km == pytest.approx(6 / 12.566, abs=0.01)
    assert report.density_level == Level.MEDIUM


def test_readings_depend_on_property_type():
    assert readings_for({"office", "shop_showroom", "warehouse", "commercial_land"}) == {
        "commercial_land": "cluster",
        "office": "cluster",
        "shop_showroom": "competition",
        "warehouse": "cluster",
    }
    assert readings_for({"apartment"}) == {}


def test_report_key_ignores_business_case_and_spacing_but_not_place_or_radius():
    key = report_key(area(), "IT services")
    assert report_key(area(), "  it   Services ") == key
    assert report_key(area(), "cafe") != key
    assert report_key(area(GeoPoint(lat=12.94, lng=77.62)), "IT services") != key
    assert report_key(area(), "IT services", radius_km=1.0) != key


def test_no_centre_means_no_report(db):
    assert get_competitor_report(area_ctx(db), area(center=None), "cafe", {"shop_showroom"}) is None


def test_a_failed_search_is_reported_and_retried_next_run(db):
    ctx = area_ctx(db)
    report, cached = get_competitor_report(ctx, area(), "cafe", {"shop_showroom"})
    assert not cached and report.status == "failed" and report.competitors == []
    assert (report.warning.section, report.warning.code) == ("competitors", "replay_miss")
    assert report.expires_at == report.fetched_at
    searches = NoSerp.calls
    _, cached = get_competitor_report(ctx, area(), "cafe", {"shop_showroom"})
    assert not cached and NoSerp.calls > searches


class OkSerp:
    calls = 0

    def search(self, engine, params, run_id=None):
        OkSerp.calls += 1
        data = {
            "local_results": [
                place(f"Co {i}", 12.936 + i * 0.001, place_id=str(i)) for i in range(5)
            ],
            "serpapi_pagination": {"next": "https://serpapi.com/..."},
        }
        return SimpleNamespace(data=data, search_id="s-1")


def ok_ctx(db):
    ctx = area_ctx(db)
    ctx.serp = OkSerp()
    return ctx


def test_a_report_is_cached_with_readings_per_profile(db):
    ctx = ok_ctx(db)
    first, cached = get_competitor_report(ctx, area(), "IT services", {"office"})
    assert not cached and first.status == "ok"
    assert (len(first.competitors), first.results_seen, first.more_available) == (5, 5, True)
    assert first.density_level == Level.MEDIUM and first.readings == {"office": "cluster"}
    searches = OkSerp.calls
    again, cached = get_competitor_report(ctx, area(), "IT services", {"shop_showroom"})
    assert cached and OkSerp.calls == searches
    assert again.readings == {"shop_showroom": "competition"}  # never taken from the cache


@pytest.mark.parametrize(
    "spoil",
    [
        lambda row: setattr(row, "expires_at", datetime.now(UTC) - timedelta(minutes=1)),
        lambda row: setattr(row, "data", {**row.data, "schema_version": 0}),
        lambda row: setattr(row, "data", {**row.data, "provider_modes": {"serpapi": "live"}}),
        lambda row: setattr(row, "data", {**row.data, "center": "not a point"}),
    ],
)
def test_a_cached_report_is_rebuilt_unless_valid(db, spoil):
    ctx = ok_ctx(db)
    get_competitor_report(ctx, area(), "IT services", {"office"})
    spoil(db.get(CompetitorReportRow, report_key(area(), "IT services")))
    db.commit()
    _, cached = get_competitor_report(ctx, area(), "IT services", {"office"})
    assert not cached
