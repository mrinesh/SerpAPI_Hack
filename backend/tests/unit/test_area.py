"""Area intelligence: parsing, distances, growth validation, summaries, cache (F-05, ADR 0016)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.core.errors import ReplayMiss, UpstreamError
from app.db.models import AreaIntelRow
from app.pipeline.enrichment.area import (
    AreaSummary,
    ClassifiedNews,
    PriceGrowthExtract,
    _summarize,
    access_from,
    apply_labels,
    departure,
    get_area_intel,
    haversine_km,
    listing_access,
    locality_key,
    parse_amenities,
    parse_centre,
    parse_commute,
    parse_duration_range,
    parse_news,
    same_event,
    supported_growth,
)
from app.pipeline.ranking import area_score
from app.reference import load_market
from app.schemas.area import Amenity, AmenityCategory, AreaAccess, AreaIntel
from app.schemas.common import GeoPoint, SerpEngine
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


def test_failed_sections_are_recorded_and_the_area_expires_at_once(db):
    ctx = area_ctx(db)
    level = Sourced(value=12_150.0, confidence=0.7, method=ExtractionMethod.LLM)
    first, cached = get_area_intel(ctx, MARKET, "whitefield", {"apartment": level})
    assert not cached and first.center is None and first.amenities == []
    assert first.section_status == {"centre": "failed", "growth": "failed", "news": "failed"}
    assert {(w.section, w.code) for w in first.warnings} == {
        ("centre", "replay_miss"),
        ("growth", "replay_miss"),
        ("news", "replay_miss"),
    }
    assert first.expires_at == first.fetched_at  # retried next run, never cached as empty
    assert first.price_levels["apartment"].value == 12_150  # still saved for inspection
    searches = NoSerp.calls
    _, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert not cached and NoSerp.calls > searches


class OkSerp:
    """Recorded-shape responses: a geocoded centre, one station, and no growth results."""

    calls = 0

    def search(self, engine, params, run_id=None):
        OkSerp.calls += 1
        q = params.get("q", "")
        if "metro" in q:
            data = {"local_results": [place("Kadugodi Tree Park", "Subway station", 12.986)]}
        elif "," in q:
            data = {"place_results": {"gps_coordinates": {"latitude": 12.97, "longitude": 77.75}}}
        else:
            data = {}
        return SimpleNamespace(data=data, search_id="s-1")


def ok_ctx(db, **settings):
    ctx = area_ctx(db)
    ctx.serp = OkSerp()
    ctx.settings = get_settings().model_copy(update=settings)
    return ctx


def test_a_complete_area_is_cached_until_it_expires(db):
    ctx = ok_ctx(db)
    first, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert not cached and first.warnings == [] and first.expires_at > first.fetched_at
    assert first.section_status["metro"] == "ok" and first.section_status["school"] == "empty"
    searches = OkSerp.calls
    _, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert cached and OkSerp.calls == searches
    row = db.get(AreaIntelRow, "bengaluru/whitefield")
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    _, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert not cached


@pytest.mark.parametrize(
    "spoil",
    [
        lambda data: {**data, "schema_version": 1},  # built by older code
        lambda data: {**data, "provider_modes": {"serpapi": "live", "llm": "live"}},
        lambda data: {**data, "center": "not a point"},  # unreadable
    ],
)
def test_a_cached_area_is_rebuilt_unless_valid_for_this_code_and_providers(db, spoil):
    ctx = ok_ctx(db)
    get_area_intel(ctx, MARKET, "whitefield")
    row = db.get(AreaIntelRow, "bengaluru/whitefield")
    row.data = spoil(row.data)
    db.commit()
    _, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert not cached


# --- news (F-05; adapted from gscode007's branch) ----------------------------------------


WHITEFIELD_PLACE = MARKET.locality("whitefield")


def article(title, link, iso_date="2026-09-20T10:00:00Z", snippet=None, source="Deccan Herald"):
    return {"title": title, "link": link, "iso_date": iso_date, "snippet": snippet,
            "source": {"name": source}}  # fmt: skip


def test_news_keeps_locality_articles_one_per_story_group_newest_first():
    data = {
        "news_results": [
            article("Metro line reaches Whitefield", "https://a.in/1", "2026-09-10T00:00:00Z"),
            {  # a story group: the first article naming the locality stands for the event
                "highlight": article("Citywide rain alert", "https://b.in/2"),
                "stories": [
                    article("Whitefield roads flooded", "https://c.in/3", "2026-09-30T00:00:00Z"),
                    article("Flooding in Whitefield again", "https://d.in/4"),
                ],
            },
            article("Koramangala cafe opens", "https://e.in/5"),  # another locality
            {"title": "A group header without a link"},
            article("Metro line reaches Whitefield", "https://a.in/1#frag"),  # same URL
            article("", "https://f.in/6"),  # malformed
            article("Whitefield news", "ftp://g.in/7"),  # not a web link
        ]
    }
    news = parse_news(data, WHITEFIELD_PLACE, "s-1")
    assert [n.title for n in news] == ["Whitefield roads flooded", "Metro line reaches Whitefield"]
    assert news[0].published_on.isoformat() == "2026-09-30" and news[0].outlet == "Deccan Herald"
    assert news[0].source.search_id == "s-1" and not news[0].classified


def test_differently_worded_reports_of_one_event_are_kept_once():
    # Recorded Koramangala headlines: seven outlets, one incident.
    a = "Man found dead inside car in Bengaluru's Koramangala"
    b = "Man found dead inside parked car in Koramangala"
    c = "Koramangala waste centre opens for practical learning"
    place = MARKET.locality("koramangala")
    assert same_event(a, b, place) and not same_event(a, c, place)


def test_recorded_whitefield_news_parses_to_ten_distinct_items():
    import json
    from pathlib import Path

    data = json.loads(
        (
            Path(__file__).parents[2] / "fixtures/serpapi/google_news/c993e726aace25efbffcad46.json"
        ).read_text(encoding="utf-8")
    )["response"]
    news = parse_news(data, WHITEFIELD_PLACE, None)
    assert len(news) == 10
    assert all("whitefield" in (n.title + (n.snippet or "")).lower() for n in news)
    dates = [n.published_on for n in news]
    assert dates == sorted(dates, reverse=True)


def test_labels_must_cover_every_article_exactly_once():
    news = parse_news(
        {
            "news_results": [
                article("Whitefield A", "https://a.in"),
                article("Whitefield B", "https://b.in"),
            ]
        },
        WHITEFIELD_PLACE,
        None,
    )
    labels = ClassifiedNews.model_validate(
        {
            "items": [
                {"index": 1, "topic": "civic", "sentiment": "negative"},
                {"index": 0, "topic": "infrastructure", "sentiment": "positive"},
            ]
        }
    )
    labelled = apply_labels(news, labels)
    assert [(n.topic, n.sentiment, n.classified) for n in labelled] == [
        ("infrastructure", "positive", True),
        ("civic", "negative", True),
    ]
    assert not news[0].classified  # the input list is not modified
    for bad in ([0], [0, 0, 1], [0, 2]):
        partial = ClassifiedNews.model_validate(
            {"items": [{"index": i, "topic": "other", "sentiment": "neutral"} for i in bad]}
        )
        with pytest.raises(UpstreamError):
            apply_labels(news, partial)


def test_an_area_cached_before_news_existed_is_rebuilt(db):
    ctx = ok_ctx(db)
    get_area_intel(ctx, MARKET, "whitefield")
    row = db.get(AreaIntelRow, "bengaluru/whitefield")
    row.data = {**row.data, "schema_version": 2}
    db.commit()
    _, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert not cached


# --- commute to job hubs (F-23, S-04, ADR 0026) -------------------------------------------


def directions(key):
    import json
    from pathlib import Path

    path = Path(__file__).parents[2] / f"fixtures/serpapi/google_maps_directions/{key}.json"
    return json.loads(path.read_text(encoding="utf-8"))["response"]


MANYATA = next(hub for hub in MARKET.job_hubs if hub.slug == "manyata")
# Whitefield centre -> Manyata, recorded in S-04 at four departures (Unix value -> minutes).
NINE_AM = "d188d252b75bb9f860a5bb78"  # 1791882000: Tue 09:00 local, the pinned departure
HALF_THREE_AM = "555bab9b60b5255bcf07acf9"  # 1791862200: 09:00 IST as a true instant
HALF_NINE_PM = "deebb8b9e081911a533e5aef"  # 1791840600: 03:00 IST as a true instant
PAST_HALF_THREE_AM = "681acc7ea82c86fd5613b6ec"  # 1790652600: two weeks before the pinned date


def minutes(key):
    return parse_commute(directions(key), MANYATA, departure(get_settings(), MARKET), None)


def test_recorded_nine_am_drive_parses_with_googles_typical_range():
    commute = parse_commute(directions(NINE_AM), MANYATA, departure(get_settings(), MARKET), "s-9")
    assert (commute.duration_min.value, commute.typical_min, commute.typical_max) == (70, 55, 110)
    assert commute.typical_text == "55 min to 1 hr 50 min"
    assert (commute.distance_km, commute.via) == (21.4, "ITPL Main Rd and NH 44")
    assert commute.hub_location == GeoPoint(lat=13.0473805, lng=77.6199556)
    [source] = commute.duration_min.sources
    assert source.engine is SerpEngine.GOOGLE_MAPS_DIRECTIONS and source.search_id == "s-9"
    assert source.url.startswith("https://www.google.com/maps/dir/")
    assert commute.depart_at.isoformat() == "2026-10-13T09:00:00+05:30"
    assert "Tuesday at 09:00" in commute.duration_min.note


def test_departure_is_read_as_local_wall_clock_time():
    """S-04: Google Maps reads `depart_at` as local time written as UTC. The value for 09:00 IST
    as a true instant reads as 03:30 (light traffic), and 03:00 IST reads as 21:30 (rush)."""
    assert minutes(HALF_THREE_AM).duration_min.value == 40
    assert minutes(HALF_NINE_PM).duration_min.value == 60
    assert minutes(NINE_AM).duration_min.value == 70
    # A departure date in the past still returns that hour's usual traffic, so the pin lasts.
    past, pinned = minutes(PAST_HALF_THREE_AM), minutes(HALF_THREE_AM)
    assert (past.duration_min.value, past.typical_text) == (40, pinned.typical_text)


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"directions": []},
        {"directions": ["not a route"]},
        {"directions": [{"duration": "40 min", "distance": 21500}]},
        {"directions": [{"duration": True, "distance": 21500}]},
        {"directions": [{"duration": 2400, "distance": 0}]},
    ],
)
def test_a_route_without_numeric_time_and_distance_is_not_a_commute(data):
    assert parse_commute(data, MANYATA, departure(get_settings(), MARKET), None) is None


def test_a_hub_with_impossible_coordinates_keeps_its_time():
    data = {
        "directions": [{"duration": 2400, "distance": 21500}],
        "places_info": [{}, {"gps_coordinates": {"latitude": 130.4, "longitude": 77.6}}],
    }
    commute = parse_commute(data, MANYATA, departure(get_settings(), MARKET), None)
    assert commute.duration_min.value == 40 and commute.hub_location is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("30\u201355 min", (30, 55)),
        ("40 min to 1 hr", (40, 60)),
        ("55 min to 1 hr 50 min", (55, 110)),
        ("1 hr 5 min to 2 hr 20 min", (65, 140)),
        ("1\u20132 hr", (60, 120)),
        ("55\u201330 min", None),  # reversed
        ("about an hour", None),
        (None, None),
    ],
)
def test_typical_duration_ranges(text, expected):
    assert parse_duration_range(text) == expected


class CommuteSerp(OkSerp):
    """OkSerp plus directions: the recorded 9 AM route, or an error for the hubs in `failing`."""

    def __init__(self, *failing: str) -> None:
        self.failing = failing

    def search(self, engine, params, run_id=None):
        if engine is not SerpEngine.GOOGLE_MAPS_DIRECTIONS:
            return super().search(engine, params, run_id)
        OkSerp.calls += 1
        if any(name in params["end_addr"] for name in self.failing):
            raise UpstreamError("SerpApi request failed: timeout")
        return SimpleNamespace(data=directions(NINE_AM), search_id="s-dir")


def test_a_failing_hub_is_reported_and_retried_without_expiring_the_area(db):
    ctx = ok_ctx(db)
    ctx.serp = CommuteSerp("Manyata")
    first, _ = get_area_intel(ctx, MARKET, "whitefield")
    assert set(first.commutes) == {"orr-bellandur", "electronic-city"}
    assert first.section_status["commute:manyata"] == "failed"
    assert [(w.section, w.code) for w in first.warnings] == [("commute:manyata", "upstream_error")]
    assert first.expires_at > first.fetched_at  # the rest of the area stays cached

    ctx.serp = CommuteSerp()
    searches = OkSerp.calls
    second, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert cached and OkSerp.calls == searches + 1  # only the missing hub is searched again
    assert set(second.commutes) == {hub.slug for hub in MARKET.job_hubs}
    assert second.warnings == [] and second.section_status["commute:manyata"] == "ok"


def test_an_area_cached_before_commutes_existed_gains_them_without_a_rebuild(db):
    ctx = ok_ctx(db)
    get_area_intel(ctx, MARKET, "whitefield")  # OkSerp: no directions data, so "empty"
    row = db.get(AreaIntelRow, "bengaluru/whitefield")
    row.data = {
        **row.data,
        "commutes": {},
        "section_status": {
            k: v for k, v in row.data["section_status"].items() if not k.startswith("commute:")
        },
    }
    db.commit()
    ctx.serp = CommuteSerp()
    area, cached = get_area_intel(ctx, MARKET, "whitefield")
    assert cached and len(area.commutes) == len(MARKET.job_hubs)


def test_no_commute_is_searched_without_a_centre(db):
    ctx = area_ctx(db)  # every search fails, the centre included
    area, _ = get_area_intel(ctx, MARKET, "whitefield")
    assert area.commutes == {} and not any(k.startswith("commute:") for k in area.section_status)
