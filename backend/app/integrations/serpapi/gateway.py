"""The single entry point for every SerpApi call (CHECKLIST I-02, I-03, I-04).

Nothing else in the codebase imports `serpapi`. Caching, record/replay and the search budget are
enforced here, so no pipeline stage can spend searches by accident.

Lookup order for `SerpApiGateway.search()`:
1. Database cache (`serp_cache`) if the entry is younger than `serpapi_cache_ttl_hours`.
2. Replay mode: the fixture `fixtures/serpapi/<engine>/<key>.json`, otherwise `ReplayMiss`.
3. Live or record mode: check the budget (`SearchBudgetExceeded`), call
   `serpapi.Client.search`, write the ledger and cache, and in record mode the fixture too.
Every lookup, live or not, is written to `search_ledger` so the run's cost is visible.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.core.errors import NotImplementedYet
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


@dataclass(frozen=True)
class SerpResponse:
    engine: SerpEngine
    params: dict[str, Any]
    data: dict[str, Any]  # raw SerpApi JSON
    search_id: str | None
    live: bool  # True when this call spent a search credit


class SerpApiGateway:
    def __init__(self, settings: Settings, db: Session) -> None:
        self._settings = settings
        self._db = db

    def search(
        self, engine: SerpEngine, params: dict[str, Any], *, run_id: str | None = None
    ) -> SerpResponse:
        raise NotImplementedYet("I-02", "SerpApi gateway search")

    def account(self) -> dict[str, Any]:
        """SerpApi Account API: plan and searches left this month. Does not use a search."""
        raise NotImplementedYet("I-05", "SerpApi account status")
