"""Stage 1, plan: investor profile -> SerpApi discovery queries (CHECKLIST F-02).

Deterministic templates, not an LLM, so the same profile always costs the same number of
searches and hits the same cache keys. A typical residential plan is one site-filtered Google
query per (locality x portal group), capped by `serpapi_run_budget`. Final templates are chosen
from the S-01 coverage spike.

Example of the intended shape (verify in S-01):
    2 BHK flat for sale Whitefield Bangalore
      site:99acres.com OR site:magicbricks.com OR site:housing.com OR site:nobroker.in
"""

from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from app.core.errors import NotImplementedYet
from app.schemas.common import SerpEngine
from app.schemas.profile import InvestorProfile


@dataclass(frozen=True)
class PlannedQuery:
    engine: SerpEngine
    params: dict[str, Any]
    purpose: str  # shown in the run log, e.g. "residential listings in Whitefield"
    locality: str | None = None
    portals: tuple[str, ...] = field(default_factory=tuple)


def plan_queries(profile: InvestorProfile, settings: Settings) -> list[PlannedQuery]:
    raise NotImplementedYet("F-02", "Query planning")
