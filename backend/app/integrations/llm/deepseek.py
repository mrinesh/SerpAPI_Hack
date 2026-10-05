"""DeepSeek implementation of `LLMProvider` via its OpenAI-compatible API (CHECKLIST I-06).

DeepSeek speaks the OpenAI chat-completions format, so this uses the `openai` SDK pointed at
`DEEPSEEK_BASE_URL`. Both tiers default to deepseek-v4-pro: the reasoning tier runs with thinking
on, the lite tier with thinking off, which is faster and spends far fewer tokens (ADR 0012).

Structured calls use JSON output mode (`response_format={"type": "json_object"}`). DeepSeek takes
no schema parameter, so the Pydantic model's JSON schema goes in the system prompt and the reply
is validated with the same model. A reply that is empty (the API occasionally returns one) or
fails validation is retried once, with the error sent back to the model.
"""

import json
from collections.abc import Callable
from typing import Any

import openai
from pydantic import ValidationError

from app.config import Settings
from app.core.errors import ProviderNotConfigured, UpstreamError
from app.integrations.llm.base import M, ModelTier

# DeepSeek's JSON mode requires the word "json" in the prompt.
_STRUCTURED_SYSTEM = (
    "Reply with one json object that conforms to this JSON Schema. No prose and no markdown "
    "fences, only the object.\n\n{schema}"
)
_RETRY_PROMPT = (
    "That reply was not valid: {error}\nReply again with only the corrected json object."
)

ClientFactory = Callable[[], Any]  # returns an object with .chat.completions.create(**kwargs)


class DeepSeekProvider:
    name = "deepseek"

    def __init__(self, settings: Settings, client_factory: ClientFactory | None = None) -> None:
        self._settings = settings
        self._client_factory = client_factory or self._default_client
        self._client: Any = None

    def model_for(self, tier: ModelTier) -> str:
        if tier is ModelTier.LITE:
            return self._settings.deepseek_model_lite
        return self._settings.deepseek_model

    def generate_structured(
        self, *, task: str, prompt: str, schema: type[M], tier: ModelTier = ModelTier.REASONING
    ) -> M:
        system = _STRUCTURED_SYSTEM.format(schema=json.dumps(schema.model_json_schema()))
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        for attempt in range(2):
            content = self._complete(task, messages, tier, json_mode=True)
            try:
                return schema.model_validate_json(content)
            except ValidationError as exc:
                error = str(exc)
            if attempt == 0:
                messages = [
                    *messages,
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": _RETRY_PROMPT.format(error=error)},
                ]
        raise UpstreamError(
            f"DeepSeek returned an invalid {schema.__name__} for {task!r} twice: {error}",
            details={"task": task},
        )

    def generate_text(
        self, *, task: str, prompt: str, tier: ModelTier = ModelTier.REASONING
    ) -> str:
        content = self._complete(task, [{"role": "user", "content": prompt}], tier)
        if not content.strip():
            raise UpstreamError(f"DeepSeek returned an empty reply for {task!r}.")
        return content

    # --- internals -------------------------------------------------------------------------

    def _default_client(self) -> openai.OpenAI:
        return openai.OpenAI(
            api_key=self._settings.deepseek_api_key,
            base_url=self._settings.deepseek_base_url,
            timeout=self._settings.deepseek_timeout_s,
        )

    def _complete(
        self, task: str, messages: list[dict[str, str]], tier: ModelTier, *, json_mode: bool = False
    ) -> str:
        if not self._settings.deepseek_api_key:
            raise ProviderNotConfigured(
                "DEEPSEEK_API_KEY is not set. Add it to .env, or use LLM_MODE=replay."
            )
        if self._client is None:
            self._client = self._client_factory()
        thinking = "enabled" if tier is ModelTier.REASONING else "disabled"
        request: dict[str, Any] = {
            "model": self.model_for(tier),
            "messages": messages,
            "max_tokens": self._settings.deepseek_max_tokens,
            "extra_body": {"thinking": {"type": thinking}},
        }
        if json_mode:
            request["response_format"] = {"type": "json_object"}
        try:
            response = self._client.chat.completions.create(**request)
        except openai.OpenAIError as exc:
            raise UpstreamError(
                f"DeepSeek request for {task!r} failed: {exc}", details={"task": task}
            ) from exc
        return response.choices[0].message.content or ""
