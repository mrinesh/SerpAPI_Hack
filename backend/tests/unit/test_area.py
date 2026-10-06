"""Area intelligence: parsing, distances, growth validation, summaries, cache (F-05, ADR 0016)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.core.errors import ReplayMiss
from app.db.models import AreaIntelRow
from app.pipeline.enrichment.area import (
    AreaSummary,
    PriceGrowthExtract,
    _summarize,
    access_from,
    get_area_intel,
    haversine_km,
    listing_access,
    locality_key,
    parse_amenities,
    parse_centre,
    supported_growth,
)
from app.pipeline.ranking import area_score
from app.reference import load_market
from app.schemas.area import Amenity, AmenityCategory, AreaAccess, AreaIntel
from app.schemas.common import GeoPoint
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef
from tests.unit.test_verification import context

MARKET = load_market("Bengaluru")
CENTRE = GeoPoint(lat=12.9698, lng=77.7500)  # Whitefield, as geocoded in F-05


def test_locality_key():
    assert locality_key("Whitefield ", "Bengaluru") == "bengaluru/whitefield"
    assert locality_key("HSR Layout", "Bengaluru") == "bengaluru/hsr-layout"


def test_haversine_matches_a_known_distance():
    # Whitefield centre to Koramangala centre (both geocoded in F-05): about 14 km by air.
    koramangala = GeoPoint(lat=12.9352, lng=77.6245)
    assert haversine_km(CENTRE, koramangala) == pytest.approx(14.1, abs=0.3)
    assert haversine_km(CENTRE, CENTRE) == 0


def test_centre_prefers_the_place_result_and_rejects_other_cities():
    place = {"place_results": {"gps_coordinates": {"latitude": 12.97, "longitude": 77.75}}}
    assert parse_centre(place, MARKET) == GeoPoint(lat=12.97, lng=77.75)
    local = {
        "local_results": [
            {"title": "x"},
            {"gps_coordinates": {"latitude": 13.0, "longitude": 77.6}},
        ]
    }
    assert parse_centre(local, MARKET) == GeoPoint(lat=13.0, lng=77.6)
    mumbai = {"place_results": {"gps_coordinates": {"latitude": 19.07, "longitude": 72.87}}}
    assert parse_centre(mumbai, MARKET) is None
    assert parse_centre({}, MARKET) is None


def place(title, kind, lat, lng=77.75):
    return {"title": title, "type": kind, "gps_coordinates": {"latitude": lat, "longitude": lng}}


def test_amenities_filter_by_type_dedupe_cut_off_and_sort():
    data = {
        "local_results": [
            place("Far School", "High school", 13.02),  # ~5.6 km
            place("KSVK School", "Educational institution", 12.974),
            place("The Bangalore School", "Preschool", 12.970),
            place("KSVK School", "High school", 12.974),  # duplicate name
            place("Spoken English Hub", "English language school", 12.971),
            place("Near School", "General education school", 12.9705),
            place("A Cafe", "Cafe", 12.970),
        ]
    }
    found = parse_amenities(data, AmenityCategory.SCHOOL, CENTRE, "s-1")
    assert [a.name for a in found] == ["Near School", "KSVK School"]
    assert found[0].distance_km < found[1].distance_km
    assert found[0].source.search_id == "s-1"


def test_metro_stations_are_kept_by_place_type_not_name():
    # Recorded: a Whitefield metro station is called "Sri Sathya Sai Hospital".
    data = {"local_results": [place("Sri Sathya Sai Hospital", "Subway station", 12.981)]}
    [station] = parse_amenities(data, AmenityCategory.METRO, CENTRE, None)
    assert station.category is AmenityCategory.METRO


WHITEFIELD = (
    "Based on government registration data, flat prices appreciated by approximately 29% in "
    "the last one year, 96% over three years, and 145% over ..."
)
KORAMANGALA = "Koramangala property prices have changed +26.9% in 1 year & +92.2% in last 5 years."
GANDHIPURAM = "Property rates in Gandhipuram have 39.63% fall in the last 1 year."


def growth(pct, evidence, confidence=0.8):
    return PriceGrowthExtract(result_index=0, pct=pct, evidence=evidence, confidence=confidence)


@pytest.mark.parametrize(
    ("found", "snippet", "expected"),
    [
        (growth(29, "appreciated by approximately 29% in the last one year"), WHITEFIELD, 29),
        (growth(26.9, "changed +26.9% in 1 year"), KORAMANGALA, 26.9),
        (growth(-39.63, "39.63% fall in the last 1 year"), GANDHIPURAM, -39.63),
        (growth(39.63, "39.63% fall in the last 1 year"), GANDHIPURAM, None),  # wrong sign
        (growth(96, "96% over three years"), WHITEFIELD, None),  # not one year
        (growth(92.2, "+92.2% in last 5 years"), KORAMANGALA, None),
        (growth(30, "appreciated by approximately 29% in the last one year"), WHITEFIELD, None),
        (growth(29, "rose 29% in the last one year"), WHITEFIELD, None),  # span not in snippet
        (growth(29, "appreciated by approximately 29% in the last one year", 0), WHITEFIELD, None),
    ],
)
def test_growth_must_be_a_quoted_one_year_change(found, snippet, expected):
    assert supported_growth(found, snippet) == expected


def test_rental_growth_is_not_price_growth():
    snippet = "Rental prices went up by 20% in the last one year."
    assert (
        supported_growth(growth(20, "Rental prices went up by 20% in the last one year"), snippet)
        is None
    )


def amenity(name, category, lat, lng=77.75):
    return Amenity(
        name=name,
        category=category,
        location=GeoPoint(lat=lat, lng=lng),
        distance_km=round(haversine_km(CENTRE, GeoPoint(lat=lat, lng=lng)), 2),
        source=SourceRef(engine="google_maps"),
    )


def area(amenities, centre=CENTRE):
    now = datetime.now(UTC)
    return AreaIntel(
        locality_key="bengaluru/whitefield",
        locality="Whitefield",
        city="Bengaluru",
        center=centre,
        amenities=amenities,
        fetched_at=now,
        expires_at=now + timedelta(days=7),
    )


AMENITIES = [
    amenity("Kadugodi Tree Park", AmenityCategory.METRO, 12.986),  # ~1.8 km
    amenity("School A", AmenityCategory.SCHOOL, 12.974),
    amenity("School B", AmenityCategory.SCHOOL, 12.99),  # ~2.3 km
    amenity("School C", AmenityCategory.SCHOOL, 13.0),  # ~3.4 km, outside 3 km
    amenity("Hospital A", AmenityCategory.HOSPITAL, 12.966),
]


def test_access_is_measured_from_the_listing_when_it_has_a_point():
    near_metro = GeoPoint(lat=12.986, lng=77.75)
    from_listing = listing_access(near_metro, area(AMENITIES))
    from_centre = listing_access(None, area(AMENITIES))
    assert from_listing.measured_from == "listing" and from_listing.metro_km == 0
    assert from_centre.measured_from == "locality centre"
    assert (from_centre.metro_name, from_centre.metro_km) == ("Kadugodi Tree Park", 1.8)
    assert (from_centre.schools_3km, from_centre.hospitals_3km) == (2, 1)
    assert listing_access(None, area([])) is None
    assert listing_access(None, None) is None


@pytest.mark.parametrize(
    ("metro_km", "schools", "hospitals", "expected"),
    [
        (0.5, 3, 3, 100),
        (4.0, 0, 0, 0),
        (None, 3, 3, 50),  # no metro found within 5 km
        (2.25, 1, 2, 0.5 * 50 + 0.25 * 100 / 3 + 0.25 * 200 / 3),
        (0.2, 9, 9, 100),  # extra amenities add nothing past 3
    ],
)
def test_area_score_curve(metro_km, schools, hospitals, expected):
    access = AreaAccess(
        metro_name="m" if metro_km is not None else None,
        metro_km=metro_km,
        schools_3km=schools,
        hospitals_3km=hospitals,
        measured_from="locality centre",
    )
    assert area_score(access) == pytest.approx(expected)
    assert area_score(None) is None


class SummaryLLM:
    def __init__(self, summary):
        self.summary = summary

    def generate_structured(self, **kwargs):
        assert kwargs["task"] == "summarize_area" and kwargs["tier"] == "lite"
        if isinstance(self.summary, Exception):
            raise self.summary
        return self.summary


GROWTH = Sourced(value=29.0, confidence=0.7, method=ExtractionMethod.LLM)


def summarize(summary):
    ctx = SimpleNamespace(llm=SummaryLLM(summary))
    centre_access = access_from(CENTRE, area(AMENITIES), "locality centre")
    return _summarize(ctx, "Whitefield", AMENITIES, GROWTH, centre_access)


def test_summary_quoting_given_figures_is_kept():
    written = AreaSummary(
        summary="2 schools within 3 km; prices rose 29% over the past 12 months.",
        infrastructure_summary="Kadugodi Tree Park metro is 1.8 km away.",
    )
    summary, infra, by_ai = summarize(written)
    assert by_ai and summary.startswith("2 schools") and "1.8 km" in infra


@pytest.mark.parametrize(
    "written",
    [
        AreaSummary(summary="Rents yield 4% a year.", infrastructure_summary="Metro 1.8 km."),
        ReplayMiss("no recording"),
    ],
)
def test_summary_falls_back_to_code_on_invented_numbers_or_errors(written):
    summary, infra, by_ai = summarize(written)
    assert not by_ai
    assert (
        infra == "Nearest metro station: Kadugodi Tree Park, 1.8 km from the centre of Whitefield."
    )
    assert summary == (
        "2 schools and 1 hospitals found within 3 km of the centre. "
        "Quoted price change: 29% over the past 12 months."
    )


class NoSerp:
    calls = 0

    def search(self, *args, **kwargs):
        NoSerp.calls += 1
        raise ReplayMiss("no recording")


def area_ctx(db):
    ctx = context()
    ctx.db, ctx.serp, ctx.settings, ctx.run_id = db, NoSerp(), get_settings(), "run-1"
    return ctx


def test_area_is_cached_until_it_expires_and_merges_price_levels(db):
    ctx = area_ctx(db)
    level = Sourced(value=12_150.0, confidence=0.7, method=ExtractionMethod.LLM)
    first, cached = get_area_intel(ctx, MARKET, "whitefield", {"apartment": level})
    assert not cached and first.center is None and first.amenities == []  # searches failed
    assert first.price_levels["apartment"].value == 12_150
    searches = NoSerp.calls
    again, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert cached and NoSerp.calls == searches
    assert again.price_levels["apartment"].value == 12_150  # kept from the first run
    row = db.get(AreaIntelRow, "bengaluru/whitefield")
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    _, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert not cached and NoSerp.calls > searches
