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
