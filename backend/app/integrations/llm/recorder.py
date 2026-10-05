"""Record/replay wrapper for any `LLMProvider` (CHECKLIST I-07).

Same three modes as the SerpApi gateway. Responses are keyed by hash(task, model, prompt):
- live: call the provider and cache in `llm_cache`;
- record: also write `fixtures/llm/<task>/<key>.json`;
- replay: serve fixtures only, so the demo runs with no DeepSeek key.
"""

from pathlib import Path

from app.config import ProviderMode
from app.core.errors import NotImplementedYet
from app.integrations.llm.base import LLMProvider, M, ModelTier


class RecordingLLM:
    def __init__(self, inner: LLMProvider, mode: ProviderMode, fixtures_dir: Path) -> None:
        self.name = f"{inner.name}+{mode}"
        self._inner = inner
        self._mode = mode
        self._fixtures_dir = fixtures_dir / "llm"

    def generate_structured(
        self, *, task: str, prompt: str, schema: type[M], tier: ModelTier = ModelTier.REASONING
    ) -> M:
        raise NotImplementedYet("I-07", "LLM record/replay")

    def generate_text(
        self, *, task: str, prompt: str, tier: ModelTier = ModelTier.REASONING
    ) -> str:
        raise NotImplementedYet("I-07", "LLM record/replay")
