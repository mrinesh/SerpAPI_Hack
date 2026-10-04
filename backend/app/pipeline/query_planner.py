"""Stage 1, plan: investor profile -> SerpApi discovery queries (CHECKLIST F-02).

Deterministic, so the same profile always costs the same searches and hits the same cache keys.
The wording is what spike S-01 tested (docs/spikes/S-01-data-coverage.md, ADR 0011):

    Google, one per locality x property type, page 1 only:
        "{type words} for sale in {locality} Bangalore under {budget}"
        + "site:99acres.com OR site:magicbricks.com OR site:nobroker.in"
        retried once without "under {budget}" if no portal result comes back
    Google Maps, one per locality, only when Apartment / Flat is chosen:
        "flats for sale {locality} Bangalore"
"""

from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.integrations.serpapi import engines
from app.reference import Market
from app.schemas.common import SerpEngine
from app.schemas.profile import InvestorProfile, PropertyType, Segment

PORTAL_FILTER = "site:99acres.com OR site:magicbricks.com OR site:nobroker.in"

# Words used in S-01. "flat" and "residential plot" matter: "plot" alone returned MATLAB
# plotting pages, and "2 BHK" in the query returned generic Bengaluru pages.
QUERY_WORDS: dict[PropertyType, str] = {
    PropertyType.APARTMENT: "flat",
    PropertyType.HOUSE_VILLA: "independent house",
    PropertyType.BUILDER_FLOOR: "builder floor",
    PropertyType.PLOT: "residential plot",
    PropertyType.OFFICE: "office space",
    PropertyType.SHOP_SHOWROOM: "shop",
    PropertyType.WAREHOUSE: "warehouse",
    PropertyType.COMMERCIAL_LAND: "commercial land",
}


@dataclass(frozen=True)
class PlannedQuery:
    engine: SerpEngine
    params: dict[str, Any]
    purpose: str  # shown in the run log, e.g. "flat in Whitefield"
    locality: str  # slug
    property_type: PropertyType
    retry_params: dict[str, Any] | None = None  # Google only: the same search without budget


def budget_phrase(budget_max_inr: int) -> str:
    """The budget as S-01 wrote it: "under 80 lakh", "under 1.5 crore" (crore singular)."""
    if budget_max_inr >= 10_000_000:
        return f"under {_compact(budget_max_inr / 10_000_000)} crore"
    return f"under {_compact(budget_max_inr / 100_000)} lakh"


def plan_queries(
    profile: InvestorProfile, settings: Settings, market: Market
) -> list[PlannedQuery]:
    planned: list[PlannedQuery] = []
    city = market.query_city_name
    for slug in profile.localities:
        locality = market.locality(slug)
        if locality is None:  # profiles are checked on save; skip anything removed since
            continue
        for property_type in profile.property_types:
            base = f"{QUERY_WORDS[property_type]} for sale in {locality.name} {city}"
            _, params = engines.google_search(
                f"{base} {budget_phrase(profile.budget_max_inr)} {PORTAL_FILTER}", settings
            )
            _, retry = engines.google_search(f"{base} {PORTAL_FILTER}", settings)
            planned.append(
                PlannedQuery(
                    engine=SerpEngine.GOOGLE,
                    params=params,
                    purpose=f"{QUERY_WORDS[property_type]} in {locality.name}",
                    locality=slug,
                    property_type=property_type,
                    retry_params=retry,
                )
            )
        if (
            profile.segment is Segment.RESIDENTIAL
            and PropertyType.APARTMENT in profile.property_types
        ):
            engine, params = engines.google_maps_search(
                f"flats for sale {locality.name} {city}", settings
            )
            planned.append(
                PlannedQuery(
                    engine=engine,
                    params=params,
                    purpose=f"housing projects in {locality.name} (Google Maps)",
                    locality=slug,
                    property_type=PropertyType.APARTMENT,
                )
            )
    return planned


def _compact(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")
