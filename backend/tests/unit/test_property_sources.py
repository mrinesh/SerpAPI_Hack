"""F-11: the detail page's "Where this came from" list (ADR 0021)."""

from datetime import UTC, datetime

from app.schemas.area import Amenity, AmenityCategory, AreaIntel, NewsItem
from app.schemas.common import SerpEngine
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef
from app.services.properties import collect_sources
from tests.unit.test_verification import candidate

PORTAL = SourceRef(engine=SerpEngine.GOOGLE, url="https://www.99acres.com/example")
LEVEL = SourceRef(engine=SerpEngine.GOOGLE, url="https://example.com/rates", search_id="s1")
OFFICE_LEVEL = SourceRef(engine=SerpEngine.GOOGLE, url="https://example.com/office", search_id="s2")
GROWTH = SourceRef(engine=SerpEngine.GOOGLE, url="https://example.com/growth", search_id="s3")
METRO = SourceRef(engine=SerpEngine.GOOGLE_MAPS, url="https://maps.example/metro", search_id="m1")
NEWS = SourceRef(engine=SerpEngine.GOOGLE_NEWS, url="https://news.example/1", search_id="n1")


def sourced(value, *sources):
    return Sourced(
        value=value, confidence=0.7, method=ExtractionMethod.REGEX, sources=list(sources)
    )


def area():
    now = datetime.now(UTC)
    return AreaIntel(
        locality_key="bengaluru/whitefield",
        locality="Whitefield",
        city="Bengaluru",
        amenities=[
            Amenity(name="Whitefield Metro", category=AmenityCategory.METRO, source=METRO),
            Amenity(name="Kadugodi Metro", category=AmenityCategory.METRO, source=METRO),
        ],
        news=[NewsItem(title="Metro line opens", url=NEWS.url, source=NEWS)],
        price_growth_pct=sourced(29.0, GROWTH),
        price_levels={
            "apartment": sourced(9000.0, LEVEL),
            "office": sourced(12000.0, OFFICE_LEVEL),
        },
        fetched_at=now,
        expires_at=now,
    )


def test_listing_then_area_figures_for_its_type_deduplicated_without_news():
    sources = collect_sources(candidate(), None, area())
    assert sources == [PORTAL, LEVEL, GROWTH, METRO]


def test_listing_only_when_there_is_no_area():
    assert collect_sources(candidate(), None, None) == [PORTAL]


def test_refs_without_a_url_or_search_id_are_dropped():
    bare = SourceRef(engine=SerpEngine.GOOGLE, title="no link")
    assert collect_sources(candidate(sources=[bare, PORTAL]), None, None) == [PORTAL]
