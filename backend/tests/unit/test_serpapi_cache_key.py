from app.integrations.serpapi.gateway import cache_key
from app.schemas.common import SerpEngine


def test_key_ignores_param_order():
    a = cache_key(SerpEngine.GOOGLE, {"q": "2 BHK Whitefield", "gl": "in", "hl": "en"})
    b = cache_key(SerpEngine.GOOGLE, {"hl": "en", "gl": "in", "q": "2 BHK Whitefield"})
    assert a == b


def test_key_ignores_api_key_and_none():
    a = cache_key(SerpEngine.GOOGLE, {"q": "x"})
    b = cache_key(SerpEngine.GOOGLE, {"q": "x", "api_key": "secret", "start": None})
    assert a == b


def test_key_depends_on_engine():
    assert cache_key(SerpEngine.GOOGLE, {"q": "x"}) != cache_key(SerpEngine.GOOGLE_NEWS, {"q": "x"})


def test_directions_key_matches_the_recorded_demo_drive():
    """The pinned departure keeps the commute key, and so its recording, stable (ADR 0026)."""
    from app.config import get_settings
    from app.integrations.serpapi.engines import google_maps_directions
    from app.schemas.common import GeoPoint

    whitefield = GeoPoint(lat=12.9698196, lng=77.7499721)
    engine, params = google_maps_directions(
        whitefield,
        "Manyata Tech Park, Nagavara, Bengaluru",
        get_settings(),
        depart_at=get_settings().commute_depart_at,
    )
    assert params["start_coords"] == "12.9698196,77.7499721"
    assert params["time"] == "depart_at:1791882000" and params["travel_mode"] == 0
    assert cache_key(engine, params) == "d188d252b75bb9f860a5bb78"
