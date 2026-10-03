"""Stage 6, rank: composite score and plain-language reasons (CHECKLIST F-04).

The score is a weighted blend computed in code (not by the LLM) so it is reproducible:
match score, yield vs target, price vs area average, area signals, and quality-flag penalties.
Weights depend on `profile.goal` and `profile.risk_appetite`; `score_breakdown` exposes them.
The LLM (`explain_recommendation`) only writes the reason, highlights and risks.
"""

from pydantic import BaseModel

from app.core.errors import NotImplementedYet
from app.pipeline.context import PipelineContext
from app.schemas.recommendation import Recommendation


class Explanation(BaseModel):
    """Output schema of the `explain_recommendation` prompt."""

    reason: str
    highlights: list[str]
    risks: list[str]


def rank(ctx: PipelineContext, run_id: str) -> list[Recommendation]:
    raise NotImplementedYet("F-04", "Ranking and explanations")
