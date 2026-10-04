"""SerpApi gateway: replay, cache, record, budgets and error handling, with a fake client."""

import json
from datetime import UTC, datetime, timedelta

import pytest
import serpapi

from app.config import ProviderMode, get_settings
from app.core.errors import ProviderNotConfigured, ReplayMiss, SearchBudgetExceeded, UpstreamError
from app.db.models import SearchLedgerRow, SerpCacheRow
from app.integrations.serpapi.gateway import SerpApiGateway, cache_key
from app.schemas.common import SerpEngine

GOOGLE = SerpEngine.GOOGLE


def response(search_id="s1", status="Success"):
    return {
        "search_metadata": {"id": search_id, "status": status},
        "search_parameters": {"engine": "google", "q": "x", "api_key": "secret"},
        "organic_results": [{"position": 1, "title": "A flat", "link": "https://example.com/a"}],
    }


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else response()
        self.error = error
        self.calls = []

    def search(self, params):
        self.calls.append(params)
        if self.error:
            raise self.error
        return self.result

    def account(self):
        return {"total_searches_left": 240, "api_key": "secret", "plan_name": "Free Plan"}


@pytest.fixture
def make_gateway(db, tmp_path):
    def build(mode=ProviderMode.LIVE, client=None, **overrides):
        settings = get_settings().model_copy(
            update={
                "serpapi_mode": mode,
                "serpapi_api_key": "key",
                "fixtures_dir": tmp_path,
                **overrides,
            }
        )
        client = client or FakeClient()
        return SerpApiGateway(settings, db, client_factory=lambda: client), client

    return build


def ledger(db):
    return [
        (row.live, row.run_id) for row in db.query(SearchLedgerRow).order_by(SearchLedgerRow.id)
    ]


def test_live_call_then_cache_hit(make_gateway, db):
    gateway, client = make_gateway()
    first = gateway.search(GOOGLE, {"q": "flats", "start": 0}, run_id="r1")
    second = gateway.search(GOOGLE, {"start": 0, "q": "flats"}, run_id="r1")
    assert (first.live, second.live) == (True, False)
    assert first.search_id == "s1"
    assert client.calls == [{"q": "flats", "start": 0, "engine": "google"}]
    assert ledger(db) == [(True, "r1"), (False, "r1")]


def test_expired_cache_is_refetched(make_gateway, db):
    gateway, client = make_gateway(serpapi_cache_ttl_hours=1)
    gateway.search(GOOGLE, {"q": "flats"})
    row = db.get(SerpCacheRow, cache_key(GOOGLE, {"q": "flats"}))
    row.fetched_at = datetime.now(UTC) - timedelta(hours=2)
    db.commit()
    assert gateway.search(GOOGLE, {"q": "flats"}).live is True
    assert len(client.calls) == 2


def test_record_writes_fixture_without_api_key(make_gateway, tmp_path):
    gateway, _ = make_gateway(mode=ProviderMode.RECORD)
    gateway.search(GOOGLE, {"q": "flats", "api_key": "secret"})
    fixture_path = tmp_path / "serpapi" / "google" / f"{cache_key(GOOGLE, {'q': 'flats'})}.json"
    text = fixture_path.read_text()
    assert "secret" not in text
    fixture = json.loads(text)
    assert fixture["params"] == {"q": "flats"}
    assert fixture["response"]["organic_results"][0]["title"] == "A flat"


def test_record_from_cache_spends_nothing(make_gateway, tmp_path):
    gateway, client = make_gateway(mode=ProviderMode.RECORD)
    gateway.search(GOOGLE, {"q": "flats"})
    fixture_path = next((tmp_path / "serpapi" / "google").glob("*.json"))
    fixture_path.unlink()
    again = gateway.search(GOOGLE, {"q": "flats"})
    assert again.live is False
    assert fixture_path.is_file()
    assert len(client.calls) == 1


def test_replay_serves_fixtures_and_never_calls_the_client(make_gateway, db):
    recorder, _ = make_gateway(mode=ProviderMode.RECORD)
    recorder.search(GOOGLE, {"q": "flats"})
    replayer, client = make_gateway(mode=ProviderMode.REPLAY, serpapi_api_key=None)
    served = replayer.search(GOOGLE, {"q": "flats"})
    assert served.live is False
    assert served.data["organic_results"][0]["title"] == "A flat"
    assert client.calls == []


def test_replay_miss(make_gateway, db):
    gateway, client = make_gateway(mode=ProviderMode.REPLAY)
    with pytest.raises(ReplayMiss) as excinfo:
        gateway.search(GOOGLE, {"q": "never recorded"})
    assert "never recorded" in excinfo.value.message
    assert client.calls == [] and ledger(db) == []


def test_run_budget(make_gateway):
    gateway, client = make_gateway(serpapi_run_budget=1)
    gateway.search(GOOGLE, {"q": "one"}, run_id="r1")
    with pytest.raises(SearchBudgetExceeded) as excinfo:
        gateway.search(GOOGLE, {"q": "two"}, run_id="r1")
    assert excinfo.value.details["scope"] == "run"
    gateway.search(GOOGLE, {"q": "two"}, run_id="r2")  # a new run has its own budget
    assert len(client.calls) == 2


def test_monthly_budget(make_gateway):
    gateway, client = make_gateway(serpapi_monthly_budget=1)
    gateway.search(GOOGLE, {"q": "one"})
    with pytest.raises(SearchBudgetExceeded) as excinfo:
        gateway.search(GOOGLE, {"q": "two"})
    assert excinfo.value.details["scope"] == "month"
    assert gateway.search(GOOGLE, {"q": "one"}).live is False  # cached answers stay free
    assert len(client.calls) == 1


def test_missing_key(make_gateway):
    gateway, client = make_gateway(serpapi_api_key=None)
    with pytest.raises(ProviderNotConfigured):
        gateway.search(GOOGLE, {"q": "flats"})
    assert client.calls == []


def test_sdk_errors_become_upstream_errors_and_are_not_cached(make_gateway, db):
    gateway, _ = make_gateway(client=FakeClient(error=serpapi.TimeoutError("timed out")))
    with pytest.raises(UpstreamError):
        gateway.search(GOOGLE, {"q": "flats"})
    assert db.query(SerpCacheRow).count() == 0 and ledger(db) == []


def test_non_success_status_is_not_cached(make_gateway, db):
    gateway, _ = make_gateway(client=FakeClient(result=response(status="Error")))
    with pytest.raises(UpstreamError):
        gateway.search(GOOGLE, {"q": "flats"})
    assert db.query(SerpCacheRow).count() == 0


def test_account_never_exposes_the_key(make_gateway):
    gateway, _ = make_gateway()
    account = gateway.account()
    assert "api_key" not in account and account["total_searches_left"] == 240


def test_budget_endpoint_in_replay_mode(client):
    body = client.get("/api/meta/budget").json()
    assert body == {
        "serpapi_mode": "replay",
        "monthly_budget": 250,
        "used_this_month": 0,
        "cache_hits_this_month": 0,
        "account_searches_left": None,
    }
