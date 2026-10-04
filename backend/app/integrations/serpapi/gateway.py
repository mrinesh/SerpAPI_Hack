"""The single entry point for every SerpApi call (CHECKLIST I-02, I-03, I-04).

Nothing else in the codebase imports `serpapi`. Caching, record/replay and the search budget are
enforced here, so no pipeline stage can spend searches by accident.

Lookup order for `SerpApiGateway.search()`:
1. **replay**: the fixture `fixtures/serpapi/<engine>/<key>.json`, otherwise `ReplayMiss`.
   Never touches the network.
2. **live / record**: the `serp_cache` row if younger than `SERPAPI_CACHE_TTL_HOURS`. In record
   mode a cache hit also writes the fixture, so recording never re-spends a search.
3. Otherwise a live call: needs `SERPAPI_API_KEY`, must fit the per-run and calendar-month
   budgets, then `serpapi.Client.search`. Only `search_metadata.status == "Success"` responses
   are cached and recorded.
Every lookup that returns a response is written to `search_ledger` (`live` says whether it spent
a search), which is what the budget and the run's cost are computed from.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import serpapi
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import ProviderMode, Settings
from app.core.errors import (
    ProviderNotConfigured,
    ReplayMiss,
    SearchBudgetExceeded,
    UpstreamError,
)
from app.db.models import SearchLedgerRow, SerpCacheRow
from app.schemas.common import SerpEngine

# Parameters that do not change the result, so they must not change the cache key.
_EXCLUDED_FROM_KEY = frozenset({"api_key", "output", "no_cache", "async"})


def cache_key(engine: SerpEngine, params: dict[str, Any]) -> str:
    """Stable key for a search: the same engine and params give the same key in any order.

    The key is also the fixture file name, so changing this function orphans every recorded
    fixture.
    """
    material = {k: v for k, v in params.items() if k not in _EXCLUDED_FROM_KEY and v is not None}
    material["engine"] = str(engine)
    blob = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def month_start(now: datetime | None = None) -> datetime:
    """Start of the current calendar month in UTC; the monthly budget counts from here."""
    now = now or datetime.now(UTC)
    return datetime(now.year, now.month, 1, tzinfo=UTC)


@dataclass(frozen=True)
class SerpResponse:
    engine: SerpEngine
    params: dict[str, Any]
    data: dict[str, Any]  # raw SerpApi JSON
    search_id: str | None
    live: bool  # True when this call spent a search credit


ClientFactory = Callable[[], Any]  # returns an object with .search(params) and .account()


class SerpApiGateway:
    def __init__(
        self, settings: Settings, db: Session, client_factory: ClientFactory | None = None
    ) -> None:
        self._settings = settings
        self._db = db
        self._client_factory = client_factory or self._default_client

    def search(
        self, engine: SerpEngine, params: dict[str, Any], *, run_id: str | None = None
    ) -> SerpResponse:
        params = {k: v for k, v in params.items() if v is not None and k != "api_key"}
        key = cache_key(engine, params)
        mode = self._settings.serpapi_mode

        if mode is ProviderMode.REPLAY:
            data = self._read_fixture(engine, key)
            if data is None:
                raise ReplayMiss(
                    f"No recorded {engine} response for {_describe(params)}. "
                    "Record it with SERPAPI_MODE=record.",
                    details={"engine": str(engine), "key": key},
                )
            return self._served(engine, params, key, data, run_id, live=False)

        cached = self._read_cache(key)
        if cached is not None:
            if mode is ProviderMode.RECORD:
                self._write_fixture(engine, key, params, cached)
            return self._served(engine, params, key, cached, run_id, live=False)

        data = self._fetch_live(engine, params, run_id)
        self._db.merge(
            SerpCacheRow(
                key=key,
                engine=str(engine),
                params=params,
                response=data,
                search_id=_search_id(data),
                fetched_at=datetime.now(UTC),
            )
        )
        if mode is ProviderMode.RECORD:
            self._write_fixture(engine, key, params, data)
        return self._served(engine, params, key, data, run_id, live=True)

    def account(self) -> dict[str, Any]:
        """SerpApi Account API: plan and searches left. Free; never counts as a search."""
        self._require_key()
        try:
            account = dict(self._client_factory().account())
        except serpapi.SerpApiError as exc:
            raise UpstreamError(f"SerpApi account request failed: {exc}") from exc
        account.pop("api_key", None)
        return account

    def live_searches(self, *, run_id: str | None = None, since: datetime | None = None) -> int:
        query = select(func.count()).select_from(SearchLedgerRow).where(SearchLedgerRow.live)
        if run_id is not None:
            query = query.where(SearchLedgerRow.run_id == run_id)
        if since is not None:
            query = query.where(SearchLedgerRow.created_at >= since)
        return self._db.scalar(query) or 0

    # --- internals -------------------------------------------------------------------------

    def _default_client(self) -> serpapi.Client:
        return serpapi.Client(
            api_key=self._settings.serpapi_api_key, timeout=self._settings.serpapi_timeout_s
        )

    def _require_key(self) -> None:
        if not self._settings.serpapi_api_key:
            raise ProviderNotConfigured(
                "SERPAPI_API_KEY is not set. Add it to .env, or use SERPAPI_MODE=replay."
            )

    def _fetch_live(
        self, engine: SerpEngine, params: dict[str, Any], run_id: str | None
    ) -> dict[str, Any]:
        self._require_key()
        self._check_budget(run_id)
        try:
            data = dict(self._client_factory().search({**params, "engine": str(engine)}))
        except serpapi.SerpApiError as exc:
            raise UpstreamError(f"SerpApi request failed: {exc}") from exc
        status = data.get("search_metadata", {}).get("status")
        if status != "Success":
            raise UpstreamError(
                f"SerpApi returned status {status!r} for {_describe(params)}: "
                f"{data.get('error', 'no error message')}"
            )
        return data

    def _check_budget(self, run_id: str | None) -> None:
        monthly = self._settings.serpapi_monthly_budget
        used_month = self.live_searches(since=month_start())
        if used_month >= monthly:
            raise SearchBudgetExceeded(
                f"Monthly search budget used up ({used_month}/{monthly}).",
                details={"scope": "month", "used": used_month, "budget": monthly},
            )
        if run_id is not None:
            per_run = self._settings.serpapi_run_budget
            used_run = self.live_searches(run_id=run_id)
            if used_run >= per_run:
                raise SearchBudgetExceeded(
                    f"This run reached its search budget ({per_run}).",
                    details={"scope": "run", "used": used_run, "budget": per_run},
                )

    def _read_cache(self, key: str) -> dict[str, Any] | None:
        row = self._db.get(SerpCacheRow, key)
        if row is None:
            return None
        fetched_at = row.fetched_at.replace(tzinfo=row.fetched_at.tzinfo or UTC)
        if datetime.now(UTC) - fetched_at > timedelta(hours=self._settings.serpapi_cache_ttl_hours):
            return None
        return row.response

    def _fixture_path(self, engine: SerpEngine, key: str) -> Path:
        return self._settings.fixtures_dir / "serpapi" / str(engine) / f"{key}.json"

    def _read_fixture(self, engine: SerpEngine, key: str) -> dict[str, Any] | None:
        path = self._fixture_path(engine, key)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))["response"]

    def _write_fixture(
        self, engine: SerpEngine, key: str, params: dict[str, Any], data: dict[str, Any]
    ) -> None:
        path = self._fixture_path(engine, key)
        if path.is_file():
            return
        response = dict(data)
        if isinstance(response.get("search_parameters"), dict):
            response["search_parameters"] = {
                k: v for k, v in response["search_parameters"].items() if k != "api_key"
            }
        path.parent.mkdir(parents=True, exist_ok=True)
        fixture = {"engine": str(engine), "params": params, "response": response}
        path.write_text(json.dumps(fixture, indent=1, ensure_ascii=False), encoding="utf-8")

    def _served(
        self,
        engine: SerpEngine,
        params: dict[str, Any],
        key: str,
        data: dict[str, Any],
        run_id: str | None,
        *,
        live: bool,
    ) -> SerpResponse:
        self._db.add(SearchLedgerRow(key=key, engine=str(engine), run_id=run_id, live=live))
        self._db.commit()
        return SerpResponse(engine, params, data, _search_id(data), live)


def _search_id(data: dict[str, Any]) -> str | None:
    return data.get("search_metadata", {}).get("id")


def _describe(params: dict[str, Any]) -> str:
    return repr(params.get("q") or params.get("data_id") or params)
