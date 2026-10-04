from datetime import UTC, datetime

import pytest

from app.config import get_settings
from app.integrations.serpapi.gateway import cache_key
from app.pipeline.query_planner import PORTAL_FILTER, budget_phrase, plan_queries
from app.reference import load_market
from app.schemas.common import SerpEngine
from app.schemas.profile import InvestorProfile

MARKET = load_market("Bengaluru")


def profile(**overrides) -> InvestorProfile:
    base = dict(
        id="p",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        name="t",
        segment="residential",
        property_types=["apartment"],
        localities=["whitefield"],
        budget_max_inr=8_000_000,
        goal="rental_income",
        target_roi_pct=4,
        risk_appetite="balanced",
    )
    return InvestorProfile(**(base | overrides))


@pytest.mark.parametrize(
    "inr,phrase",
    [
        (6_000_000, "under 60 lakh"),
        (8_000_000, "under 80 lakh"),
        (9_950_000, "under 99.5 lakh"),
        (10_000_000, "under 1 crore"),
        (15_000_000, "under 1.5 crore"),
        (30_000_000, "under 3 crore"),
    ],
)
def test_budget_phrase(inr, phrase):
    assert budget_phrase(inr) == phrase


def test_one_google_search_per_locality_and_type_plus_maps_for_flats():
    queries = plan_queries(
        profile(property_types=["apartment", "plot"], localities=["hebbal", "yelahanka"]),
        get_settings(),
        MARKET,
    )
    assert [(q.engine, q.params["q"].removesuffix(f" {PORTAL_FILTER}")) for q in queries] == [
        (SerpEngine.GOOGLE, "flat for sale in Hebbal Bangalore under 80 lakh"),
        (SerpEngine.GOOGLE, "residential plot for sale in Hebbal Bangalore under 80 lakh"),
        (SerpEngine.GOOGLE_MAPS, "flats for sale Hebbal Bangalore"),
        (SerpEngine.GOOGLE, "flat for sale in Yelahanka Bangalore under 80 lakh"),
        (SerpEngine.GOOGLE, "residential plot for sale in Yelahanka Bangalore under 80 lakh"),
        (SerpEngine.GOOGLE_MAPS, "flats for sale Yelahanka Bangalore"),
    ]
    assert queries[0].retry_params["q"] == f"flat for sale in Hebbal Bangalore {PORTAL_FILTER}"
    assert queries[2].retry_params is None


def test_no_maps_search_without_flats_or_for_commercial():
    houses = plan_queries(profile(property_types=["house_villa"]), get_settings(), MARKET)
    shops = plan_queries(
        profile(segment="commercial", property_types=["shop_showroom"], business_type="Cafe"),
        get_settings(),
        MARKET,
    )
    assert {q.engine for q in houses + shops} == {SerpEngine.GOOGLE}


def test_demo_profiles_replay_from_recorded_fixtures():
    """The planner reproduces S-01's exact searches, so these profiles run with no credits."""
    settings = get_settings()
    demos = [
        profile(),
        profile(
            segment="commercial",
            property_types=["office"],
            business_type="Cafe",
            localities=["koramangala"],
            budget_max_inr=30_000_000,
        ),
    ]
    for demo in demos:
        for query in plan_queries(demo, settings, MARKET):
            path = settings.fixtures_dir / "serpapi" / str(query.engine)
            assert (path / f"{cache_key(query.engine, query.params)}.json").is_file(), query.purpose
