"""Stage 3, clean: normalise, classify and de-duplicate hits into `Listing`s (CHECKLIST F-02).

Deterministic parsing runs first and the LLM only fills the gaps (stage 4), so cheap and exact
extraction wins wherever the text is regular. Expected behaviour of the parsers, as examples
that become unit tests:

    parse_price_inr("₹85 L")               -> 8_500_000
    parse_price_inr("1.25 Cr")             -> 12_500_000
    parse_price_inr("₹ 45,000 / month")    -> 45_000
    parse_area_sqft("1,250 sq.ft")         -> 1250.0
    parse_area_sqft("116 sq.m")            -> 1248.6
    detect_portal("https://www.99acres.com/...")  -> Portal.NINETY_NINE_ACRES
"""

from app.core.errors import NotImplementedYet
from app.schemas.listing import Listing, Portal, RawSearchHit


def parse_price_inr(text: str) -> int | None:
    raise NotImplementedYet("F-02", "Price parsing")


def parse_area_sqft(text: str) -> float | None:
    raise NotImplementedYet("F-02", "Area parsing")


def detect_portal(url: str) -> Portal:
    raise NotImplementedYet("F-02", "Portal detection")


def canonical_url(url: str) -> str:
    """Strip tracking params, fragments and mobile prefixes so one property has one URL."""
    raise NotImplementedYet("F-02", "URL canonicalisation")


def normalize_hits(hits: list[RawSearchHit]) -> list[Listing]:
    """Parse, classify (`ResultKind`) and merge hits that point at the same property.

    Duplicates are matched by canonical URL first, then by fuzzy title + price + locality
    (rapidfuzz). Merged listings keep every source in `Listing.sources`.
    """
    raise NotImplementedYet("F-02", "Hit normalisation and de-duplication")
