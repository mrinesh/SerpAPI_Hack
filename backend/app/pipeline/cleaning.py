"""Stage 3, clean: turn portal search pages and Maps places into candidates (CHECKLIST F-02).

Google returns the portals' search pages, never single listings, but their snippets quote real
entries (ADR 0011, spike S-01). Every pattern here was seen in the recorded fixtures, and the
tests replay those exact strings. Examples:

    99acres      "SOWPARNIKA COLUMNS · ₹60 Lac. ₹8,185 /sqft"
    99acres      "Resale ₹76 Lac ₹10,340 /sqft Ready To Move 735 sqft(68 sqm)"
    NoBroker     "2 BHK Apartment In Rs Abode Apartments For Sale In Hebbal · ₹7,600/sq.ft
                  · 1250 sqft"
    MagicBricks  "₹1.45 Cr 2 BHK. 2 BHK Builder Floor for Sale in Jayanagar Bangalore.
                  Super Area. 1100 sqft."

Parsing is deterministic; the LLM (F-03) only fills gaps later. Confidence is fixed per
extraction method: read from text 0.8, computed from other values 0.6, taken from the search
itself 0.5, a SerpApi Maps field 0.9.
"""

import hashlib
import html
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlencode, urlparse

from rapidfuzz import fuzz

from app.reference import Market
from app.schemas.common import SerpEngine
from app.schemas.listing import Listing, Portal, RawSearchHit, ResultKind, SaleStatus
from app.schemas.profile import (
    PROPERTY_TYPE_LABELS,
    SEGMENT_PROPERTY_TYPES,
    PropertyType,
    Segment,
)
from app.schemas.provenance import ExtractionMethod, Sourced, SourceRef

PORTAL_HOSTS = {
    "99acres.com": Portal.NINETY_NINE_ACRES,
    "magicbricks.com": Portal.MAGICBRICKS,
    "nobroker.in": Portal.NOBROKER,
}

# Google Maps place types seen for housing in S-01 ("flats for sale <locality>").
HOUSING_PLACE_TYPES = frozenset(
    {
        "Apartment complex",
        "Apartment building",
        "Condominium complex",
        "Gated community",
        "Furnished apartment building",
    }
)

SQ_M_TO_SQ_FT = 10.7639  # 1 m = 3.28084 ft
SQ_YD_TO_SQ_FT = 9.0  # 1 yd = 3 ft
UNIT_INR = {"lac": 100_000, "lakh": 100_000, "cr": 10_000_000, "crore": 10_000_000}

CONFIDENCE = {
    ExtractionMethod.REGEX: 0.8,
    ExtractionMethod.COMPUTED: 0.6,
    ExtractionMethod.QUERY: 0.5,
    ExtractionMethod.SERPAPI_FIELD: 0.9,
}

_UNIT = r"(?:lacs?|lakhs?|crores?|cr)"
_PRICE = re.compile(
    rf"(?:₹|\brs\.?)?\s?(?P<low>\d+(?:\.\d+)?)\s*(?P<lowunit>{_UNIT})?\.?"
    rf"(?:\s*-\s*(?P<high>\d+(?:\.\d+)?))?\s*(?P<unit>{_UNIT})\b(?P<plus>\+)?",
    re.IGNORECASE,
)
_PRICE_PER_SQFT = re.compile(r"₹\s?(?P<value>[\d,]+(?:\.\d+)?)\s*/\s*sq\.?\s?ft", re.IGNORECASE)
_AREA = re.compile(
    r"(?<![₹\d,.])(?P<value>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<unit>sq\.?\s?ft\.?|sqft|sq\.?\s?yd|sqyd|sq\.?\s?m\b|sqm)",
    re.IGNORECASE,
)
_BHK = re.compile(r"(?<![\d,]\s)(?<![\d,])(?P<n>\d)\s?\+?\s?BHK", re.IGNORECASE)
# Words that make a number a filter, statistic or instalment rather than an asking price,
# e.g. "priced between ₹68.55 lakh", "average price of ₹4.59 Cr", "within ₹ 1 Crore",
# "EMI: ₹2 Lacs".
_NOT_A_PRICE_BEFORE = re.compile(
    r"(?:average|median|between|spanning|from|starting|starts|upto|up to|within|under|below|"
    r"above|budget of|emi:?|\band|\bto)\s*(?:price of\s*)?$",
    re.IGNORECASE,
)
_PER_MONTH_AFTER = re.compile(r"^\s*(?:/\s*m\b|/\s*month|per month)", re.IGNORECASE)
_SEGMENT_SPLIT = re.compile(r"\s+[;・]\s+|\s*(?:\.\.\.|…)\s*")
_CAPS_NAME = re.compile(r"(?P<name>[A-Z0-9][A-Z0-9&'.\- ]{2,}[A-Z0-9])\s*·\s*$")
_NOBROKER_NAME = re.compile(
    r"\d\+?\s?BHK\s+\w+\s+In\s+(?P<name>.+?)\s+For Sale In\b", re.IGNORECASE
)
_FOR_SALE_SENTENCE = re.compile(r"[^.;·]*\bfor sale in\b[^.;·]*", re.IGNORECASE)
# Search-page blurbs, not entries: "Find over 28+ 2 BHK Flats for sale in …", "Choose from …".
_PAGE_BLURB = re.compile(r"^(?:find|choose|explore|buy|search)\b|\d+\+", re.IGNORECASE)
_STATUS = (
    (re.compile(r"under construction", re.I), SaleStatus.UNDER_CONSTRUCTION),
    (re.compile(r"ready to move", re.I), SaleStatus.READY_TO_MOVE),
    (re.compile(r"new launch", re.I), SaleStatus.NEW_LAUNCH),
    (re.compile(r"\bresale\b", re.I), SaleStatus.RESALE),
)
# Most specific first: "builder floor apartment" is a builder floor, not an apartment.
_TYPE_WORDS = (
    (re.compile(r"builder floor", re.I), PropertyType.BUILDER_FLOOR),
    (re.compile(r"commercial land|commercial/inst", re.I), PropertyType.COMMERCIAL_LAND),
    (re.compile(r"\bplots?\b|residential land", re.I), PropertyType.PLOT),
    (re.compile(r"\bvillas?\b|\bhouses?\b", re.I), PropertyType.HOUSE_VILLA),
    (re.compile(r"\bflats?\b|\bapartments?\b", re.I), PropertyType.APARTMENT),
    (re.compile(r"\boffice", re.I), PropertyType.OFFICE),
    (re.compile(r"\bshops?\b|\bshowrooms?\b", re.I), PropertyType.SHOP_SHOWROOM),
    (re.compile(r"warehouse|godown", re.I), PropertyType.WAREHOUSE),
)
_RENTAL_TITLE = re.compile(r"\b(?:for|on) rent\b|\brental\b", re.IGNORECASE)


# --- small parsers ------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """NFKC (MagicBricks titles write "₹ 1 Crore" in mathematical-bold characters), HTML
    entities ("&amp;" in NoBroker snippets), and whitespace."""
    text = html.unescape(unicodedata.normalize("NFKC", text))
    return re.sub(r"\s+", " ", text).strip()


def detect_portal(url: str) -> Portal | None:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return PORTAL_HOSTS.get(host)


def is_rental_page(title: str, url: str) -> bool:
    """MagicBricks marks for-rent search pages "-pppfr"; others say "for Rent" in the title."""
    return "-pppfr" in url or bool(_RENTAL_TITLE.search(title))


@dataclass(frozen=True)
class PriceMention:
    inr: int
    start: int
    end: int
    note: str | None


def find_prices(text: str) -> list[PriceMention]:
    """Asking prices in `text`, skipping filters, statistics and monthly amounts."""
    prices = []
    for m in _PRICE.finditer(text):
        before, after = text[max(0, m.start() - 30) : m.start()], text[m.end() :]
        if _NOT_A_PRICE_BEFORE.search(before) or _PER_MONTH_AFTER.match(after):
            continue
        low_unit = (m["lowunit"] or m["unit"]).lower()
        inr = round(float(m["low"]) * UNIT_INR[_unit_key(low_unit)])
        note = None
        if m["high"]:
            note = f"price range up to {m['high']} {m['unit']}; lower bound used"
        elif m["plus"]:
            note = "starting price"
        if inr > 0:
            prices.append(PriceMention(inr, m.start(), m.end(), note))
    return prices


def parse_price_inr(text: str) -> int | None:
    prices = find_prices(normalize_text(text))
    return prices[0].inr if prices else None


def parse_price_per_sqft(text: str) -> float | None:
    m = _PRICE_PER_SQFT.search(normalize_text(text))
    return float(m["value"].replace(",", "")) if m else None


def parse_area_sqft(text: str) -> float | None:
    """First area in sq ft, sq m or sq yd, as sq ft. Skips ranges like "from 2000 sq ft"."""
    text = normalize_text(text)
    for m in _AREA.finditer(text):
        if _NOT_A_PRICE_BEFORE.search(text[max(0, m.start() - 30) : m.start()]):
            continue
        value = float(m["value"].replace(",", ""))
        unit = m["unit"].lower().replace(".", "").replace(" ", "")
        if unit.startswith("sqm"):
            value *= SQ_M_TO_SQ_FT
        elif unit.startswith("sqyd"):
            value *= SQ_YD_TO_SQ_FT
        return round(value, 1)
    return None


def parse_bedrooms(text: str) -> int | None:
    m = _BHK.search(normalize_text(text))
    return int(m["n"]) if m else None


def parse_status(text: str) -> SaleStatus | None:
    return next((status for rx, status in _STATUS if rx.search(text)), None)


def parse_property_type(text: str, segment: Segment) -> PropertyType | None:
    """The first property-type word in `text` that belongs to the profile's segment."""
    allowed = SEGMENT_PROPERTY_TYPES[segment]
    return next((t for rx, t in _TYPE_WORDS if t in allowed and rx.search(text)), None)


def _unit_key(unit: str) -> str:
    if unit.startswith("lac") or unit.startswith("lakh"):
        return "lac"
    return "cr"


# --- snippet entries ----------------------------------------------------------------------


@dataclass
class SnippetEntry:
    """One priced entry quoted in a search page's snippet."""

    evidence: str
    price_inr: int | None
    price_note: str | None = None
    price_computed: bool = False
    price_per_sqft: float | None = None
    size_sqft: float | None = None
    size_computed: bool = False
    bedrooms: int | None = None
    status: SaleStatus | None = None
    project_name: str | None = None  # a real project name, used to match Maps places
    headline: str | None = None


def snippet_entries(snippet: str) -> list[SnippetEntry]:
    """Split a snippet into priced entries. Entries without any price are dropped."""
    entries = []
    for segment in _SEGMENT_SPLIT.split(normalize_text(snippet)):
        prices = find_prices(segment)
        if not prices:
            ppsf = _PRICE_PER_SQFT.search(segment)
            if ppsf:  # NoBroker quotes some entries by price per sq ft and size only
                entries.append(_entry(segment, segment[: ppsf.start()], segment, None))
            continue
        for i, price in enumerate(prices):
            head = segment[: price.start] if i == 0 else ""
            end = prices[i + 1].start if i + 1 < len(prices) else len(segment)
            body = segment[price.start : end]
            entries.append(_entry(segment if len(prices) == 1 else body, head, body, price))
    return [e for e in entries if e.price_inr]


def _entry(evidence: str, head: str, body: str, price: PriceMention | None) -> SnippetEntry:
    text = f"{head} {body}"
    ppsf = parse_price_per_sqft(body)
    size = parse_area_sqft(body) or parse_area_sqft(head)
    entry = SnippetEntry(
        evidence=evidence.strip(" ·."),
        price_inr=price.inr if price else None,
        price_note=price.note if price else None,
        price_per_sqft=ppsf,
        size_sqft=size,
        bedrooms=parse_bedrooms(head) or parse_bedrooms(body),
        status=parse_status(text),
        project_name=_caps_name(head) or _nobroker_name(text),
        headline=_headline(head) or _headline(body),
    )
    if entry.price_inr is None and ppsf and size:
        entry.price_inr, entry.price_computed = round(ppsf * size), True
        entry.price_note = "computed from price per sq ft × size"  # noqa: RUF001
    elif entry.size_sqft is None and ppsf and entry.price_inr:
        entry.size_sqft, entry.size_computed = round(entry.price_inr / ppsf, 1), True
    return entry


def _caps_name(head: str) -> str | None:
    """99acres puts the project in capitals before the price: "SOWPARNIKA COLUMNS · ₹60 Lac"."""
    if m := _CAPS_NAME.search(head.rstrip(" ·.") + " ·"):
        return m["name"].title()
    return None


def _nobroker_name(text: str) -> str | None:
    """NoBroker: "2 BHK Apartment In <project> For Sale In <locality>"."""
    if m := _NOBROKER_NAME.search(text):
        return m["name"].strip(" ,")
    return None


def _headline(text: str) -> str | None:
    if m := _FOR_SALE_SENTENCE.search(text):
        line = re.sub(r"\s+(?:resale|sale)$", "", m.group(0).strip(" ,.·"), flags=re.I)
        if len(re.findall(r"[A-Za-z]", line)) >= 8 and not _PAGE_BLURB.search(line):
            return line[:90]
    return None


# --- candidates ---------------------------------------------------------------------------


@dataclass
class CleaningResult:
    listings: list[Listing]
    pages: int = 0  # portal pages read
    entries: int = 0  # priced entries parsed before de-duplication
    projects: int = 0  # Maps housing places
    matched_projects: int = 0  # Maps places merged into a priced entry
    merged_duplicates: int = 0
    notes: list[str] = field(default_factory=list)


def normalize_hits(
    hits: list[RawSearchHit], *, segment: Segment, market: Market, now: datetime
) -> CleaningResult:
    """Parse, merge and de-duplicate hits into candidates."""
    result = CleaningResult(listings=[])
    entries: list[Listing] = []
    places: list[RawSearchHit] = []
    for hit in hits:
        if hit.engine is SerpEngine.GOOGLE_MAPS:
            places.append(hit)
            continue
        result.pages += 1
        for entry in snippet_entries(hit.snippet or ""):
            entries.append(_entry_listing(entry, hit, segment, market, now))
    result.entries = len(entries)
    result.projects = len(places)

    entries, result.merged_duplicates = _merge_duplicates(entries)
    unmatched = _attach_places(entries, places, result)
    projects = [_project_listing(place, segment, now) for place in unmatched]
    result.listings = entries + projects
    return result


def _entry_listing(
    entry: SnippetEntry, hit: RawSearchHit, segment: Segment, market: Market, now: datetime
) -> Listing:
    portal = detect_portal(hit.link or "")
    source = SourceRef(engine=hit.engine, url=hit.link, title=hit.title, search_id=hit.search_id)
    type_from_text = parse_property_type(f"{entry.evidence} {hit.title}", segment)
    property_type = type_from_text or hit.property_type
    locality = market.locality(hit.locality)
    bedrooms = entry.bedrooms or parse_bedrooms(hit.title)
    name = entry.project_name or entry.headline or _fallback_name(bedrooms, property_type, locality)
    identity = "|".join(
        str(x)
        for x in (
            "entry",
            portal,
            hit.locality,
            _norm(name),
            entry.price_inr,
            entry.price_per_sqft,
            entry.size_sqft,
        )
    )
    price_method = ExtractionMethod.COMPUTED if entry.price_computed else ExtractionMethod.REGEX
    size_method = ExtractionMethod.COMPUTED if entry.size_computed else ExtractionMethod.REGEX
    return Listing(
        id=_hash(identity),
        kind=ResultKind.SNIPPET_ENTRY,
        portal=portal,
        name=name,
        url=hit.link,
        segment=segment,
        property_type=_sourced(
            property_type,
            ExtractionMethod.REGEX if type_from_text else ExtractionMethod.QUERY,
            source,
            None if type_from_text else "the property type that was searched for",
        ),
        locality=_sourced(
            hit.locality,
            ExtractionMethod.QUERY,
            source,
            "the locality that was searched for; the page may cover nearby areas",
        ),
        price_inr=_sourced(entry.price_inr, price_method, source, entry.price_note),
        price_per_sqft=_sourced(entry.price_per_sqft, ExtractionMethod.REGEX, source),
        size_sqft=_sourced(
            entry.size_sqft,
            size_method,
            source,
            "computed from price ÷ price per sq ft" if entry.size_computed else None,
        ),
        bedrooms=_page_fallback(entry.bedrooms, parse_bedrooms(hit.title), source),
        status=_page_fallback(entry.status, parse_status(hit.title), source),
        location=_sourced(None, ExtractionMethod.SERPAPI_FIELD, None),
        evidence=entry.evidence,
        sources=[source],
        first_seen_at=now,
        last_seen_at=now,
    )


def _project_listing(place: RawSearchHit, segment: Segment, now: datetime) -> Listing:
    source = SourceRef(
        engine=place.engine, url=_maps_url(place), title=place.title, search_id=place.search_id
    )
    return Listing(
        id=_hash(f"project|{place.place_id or _norm(place.title)}"),
        kind=ResultKind.PROJECT,
        portal=Portal.GOOGLE_MAPS,
        name=place.title,
        url=_maps_url(place),
        segment=segment,
        property_type=_sourced(
            place.property_type,
            ExtractionMethod.QUERY,
            source,
            f"Google Maps place type: {place.place_type}",
        ),
        locality=_sourced(
            place.locality, ExtractionMethod.QUERY, source, "the locality that was searched for"
        ),
        price_inr=_sourced(None, ExtractionMethod.REGEX, None, "no price quoted for this project"),
        price_per_sqft=_sourced(None, ExtractionMethod.REGEX, None),
        size_sqft=_sourced(None, ExtractionMethod.REGEX, None),
        bedrooms=_sourced(None, ExtractionMethod.REGEX, None),
        status=_sourced(None, ExtractionMethod.REGEX, None),
        location=_sourced(place.gps, ExtractionMethod.SERPAPI_FIELD, source),
        rating=place.rating,
        reviews=place.reviews,
        evidence=place.address,
        sources=[source],
        first_seen_at=now,
        last_seen_at=now,
    )


def _merge_duplicates(entries: list[Listing]) -> tuple[list[Listing], int]:
    """Same entry quoted by several pages: same id, or same locality and price with
    near-identical names (rapidfuzz token_sort_ratio >= 90). Sources are combined."""
    kept: list[Listing] = []
    merged = 0
    for entry in entries:
        twin = next((k for k in kept if _same_entry(k, entry)), None)
        if twin is None:
            kept.append(entry)
            continue
        merged += 1
        twin.sources.extend(s for s in entry.sources if s not in twin.sources)
    return kept, merged


def _same_entry(a: Listing, b: Listing) -> bool:
    if a.id == b.id:
        return True
    return (
        a.locality.value == b.locality.value
        and a.price_inr.value == b.price_inr.value
        and fuzz.token_sort_ratio(_norm(a.name), _norm(b.name)) >= 90
    )


def _attach_places(
    entries: list[Listing], places: list[RawSearchHit], result: CleaningResult
) -> list[RawSearchHit]:
    """Give priced entries the GPS of the Maps project with the same name; return the rest."""
    unmatched = []
    for place in places:
        matches = [
            e
            for e in entries
            if e.locality.value == place.locality
            and fuzz.token_sort_ratio(_norm(e.name), _norm(place.title)) >= 90
        ]
        if not matches:
            unmatched.append(place)
            continue
        result.matched_projects += 1
        source = SourceRef(
            engine=place.engine, url=_maps_url(place), title=place.title, search_id=place.search_id
        )
        for entry in matches:
            entry.location = _sourced(
                place.gps,
                ExtractionMethod.SERPAPI_FIELD,
                source,
                f"matched to Google Maps place {place.title!r}",
            )
            entry.rating, entry.reviews = place.rating, place.reviews
            entry.sources.append(source)
    return unmatched


def _page_fallback(from_entry, from_title, source: SourceRef) -> Sourced:
    """Prefer the entry's own text; else the page title, which states the page's filter
    (e.g. "2 BHK Flats in Thubarahalli", "Ready to move Flats / Apartments in Whitefield")."""
    if from_entry is not None:
        return _sourced(from_entry, ExtractionMethod.REGEX, source)
    note = "from the page title" if from_title is not None else None
    return _sourced(from_title, ExtractionMethod.REGEX, source, note)


def _fallback_name(bedrooms: int | None, property_type: PropertyType, locality) -> str:
    bhk = f"{bedrooms} BHK " if bedrooms else ""
    where = f" in {locality.name}" if locality else ""
    return f"{bhk}{PROPERTY_TYPE_LABELS[property_type]}{where}"


def _maps_url(place: RawSearchHit) -> str | None:
    """Google Maps URLs "search" action with a place ID.

    Format: developers.google.com/maps/documentation/urls/get-started (checked 2026-10-04).
    """
    if not place.place_id:
        return None
    return "https://www.google.com/maps/search/?" + urlencode(
        {"api": 1, "query": place.title, "query_place_id": place.place_id}
    )


def _sourced(value, method: ExtractionMethod, source: SourceRef | None, note: str | None = None):
    if value is None:
        return Sourced(value=None, confidence=0.0, method=method, note=note)
    return Sourced(
        value=value,
        confidence=CONFIDENCE[method],
        method=method,
        sources=[source] if source else [],
        note=note,
    )


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:24]
