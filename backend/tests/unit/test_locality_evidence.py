"""Locality evidence in cleaning and the location_mismatch flag (I-12, ADR 0024)."""

from datetime import UTC, datetime

from app.pipeline.cleaning import normalize_hits
from app.pipeline.quality import location_flag
from app.pipeline.verification import verify
from app.reference import load_market
from app.schemas.common import GeoPoint, SerpEngine
from app.schemas.listing import MatchVerdict, QualityFlagKind, RawSearchHit
from app.schemas.provenance import ExtractionMethod
from tests.unit.test_verification import candidate, context

MARKET = load_market("Bengaluru")
NOW = datetime.now(UTC)


def hit(snippet=None, title="Flats for Sale in Whitefield", **extra):
    return RawSearchHit(
        engine=extra.pop("engine", SerpEngine.GOOGLE),
        query="flats for sale in Whitefield",
        locality="whitefield",
        property_type="apartment",
        title=title,
        link=extra.pop("link", "https://www.99acres.com/flats-in-whitefield"),
        snippet=snippet,
        fetched_at=NOW,
        **extra,
    )


def clean(*hits):
    return normalize_hits(list(hits), segment="residential", market=MARKET, now=NOW).listings


def test_entry_text_naming_the_locality_confirms_it():
    [listing] = clean(hit("3 BHK Flat in Whitefield for sale ₹80 Lac 1,200 sqft"))
    assert listing.locality.method is ExtractionMethod.REGEX
    assert listing.locality.confidence == 0.8
    assert listing.locality.note == "named in the result text"
    assert listing.named_localities == ["whitefield"]


def test_only_the_page_title_naming_it_is_weaker_evidence():
    [listing] = clean(hit("3 BHK Flat for sale ₹80 Lac 1,200 sqft"))
    assert (listing.locality.method, listing.locality.confidence) == (ExtractionMethod.REGEX, 0.7)
    assert "page title" in listing.locality.note and listing.named_localities == []


def test_nothing_naming_it_leaves_the_query():
    [listing] = clean(hit("3 BHK Flat for sale ₹80 Lac 1,200 sqft", title="Flats for Sale"))
    assert (listing.locality.method, listing.locality.confidence) == (ExtractionMethod.QUERY, 0.5)


def test_text_naming_another_locality_lowers_confidence_and_records_it():
    [listing] = clean(hit("3 BHK Flat in Marathahalli for sale ₹80 Lac 1,200 sqft"))
    assert listing.locality.value == "whitefield"  # the slug never changes
    assert (listing.locality.method, listing.locality.confidence) == (ExtractionMethod.QUERY, 0.3)
    assert listing.named_localities == ["marathahalli"]


def place(address, title="Prestige Lakeside"):
    return hit(
        engine=SerpEngine.GOOGLE_MAPS,
        title=title,
        link=None,
        address=address,
        gps=GeoPoint(lat=12.97, lng=77.75),
        place_id="p-1",
    )


def test_a_maps_address_confirms_a_project():
    [project] = clean(place("Kadugodi, Whitefield, Bengaluru, Karnataka 560067"))
    assert (project.locality.method, project.locality.confidence) == (
        ExtractionMethod.SERPAPI_FIELD,
        0.9,
    )
    assert project.locality.note == "named in the Google Maps address"


def test_a_matched_project_address_confirms_an_entry_with_no_place_in_its_text():
    entry = hit("PRESTIGE LAKESIDE · ₹80 Lac · 1,200 sqft", title="Flats for Sale")
    [listing] = clean(entry, place("Whitefield, Bengaluru", title="Prestige Lakeside"))
    assert listing.locality.note == "named in the Google Maps address"
    assert listing.named_localities == ["whitefield"]


def test_mismatch_flag_is_high_outside_the_profile_and_medium_inside():
    listing = candidate(named_localities=["marathahalli"])
    flag = location_flag(listing, ["whitefield"], MARKET)
    assert flag.kind is QualityFlagKind.LOCATION_MISMATCH and flag.severity == "high"
    assert "Marathahalli, not Whitefield" in flag.reason
    flag = location_flag(listing, ["whitefield", "marathahalli"], MARKET)
    assert flag.severity == "medium" and "also one of your localities" in flag.reason
    assert location_flag(candidate(named_localities=["whitefield"]), ["whitefield"], MARKET) is None
    assert location_flag(candidate(), ["whitefield"], MARKET) is None


def test_verification_caps_a_listing_its_own_text_places_elsewhere():
    result = verify(context(), candidate(named_localities=["marathahalli"]))
    assert result.verdict is MatchVerdict.WEAK and result.match_score <= 59
    assert any(flag.kind is QualityFlagKind.LOCATION_MISMATCH for flag in result.flags)
    assert any("Marathahalli" in reason for reason in result.mismatches)
