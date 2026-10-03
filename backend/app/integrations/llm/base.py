"""The LLM interface the pipeline depends on. Gemini is the only implementation today
(docs/decisions/0005-llm-behind-an-interface.md)."""

from enum import StrEnum
from typing import Protocol, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


class ModelTier(StrEnum):
    REASONING = "reasoning"  # scoring, explanations, summaries
    LITE = "lite"  # high-volume field extraction


class LLMProvider(Protocol):
    name: str

    def generate_structured(
        self, *, task: str, prompt: str, schema: type[M], tier: ModelTier = ModelTier.REASONING
    ) -> M:
        """Return an instance of `schema`, validated. `task` names the prompt (for caching and
        logs), e.g. "verify_listing"."""
        ...

    def generate_text(
        self, *, task: str, prompt: str, tier: ModelTier = ModelTier.REASONING
    ) -> str: ...
