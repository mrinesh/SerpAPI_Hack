"""Gemini implementation of `LLMProvider` via the `google-genai` SDK (CHECKLIST I-06).

Structured calls pass the Pydantic model as `response_schema` with
`response_mime_type="application/json"` in `types.GenerateContentConfig`, then validate the
reply with the same model. A reply that fails validation is retried once with the validation
error appended to the prompt.
"""

from app.config import Settings
from app.core.errors import NotImplementedYet
from app.integrations.llm.base import M, ModelTier


class GeminiProvider:
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def model_for(self, tier: ModelTier) -> str:
        if tier is ModelTier.LITE:
            return self._settings.gemini_model_lite
        return self._settings.gemini_model

    def generate_structured(
        self, *, task: str, prompt: str, schema: type[M], tier: ModelTier = ModelTier.REASONING
    ) -> M:
        raise NotImplementedYet("I-06", "Gemini structured generation")

    def generate_text(
        self, *, task: str, prompt: str, tier: ModelTier = ModelTier.REASONING
    ) -> str:
        raise NotImplementedYet("I-06", "Gemini text generation")
