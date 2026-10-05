"""Validated LLM cache and record/replay. Replay never calls the inner provider (I-07)."""

import hashlib
import json
import re
from contextlib import suppress
from pathlib import Path

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.config import ProviderMode
from app.core.errors import ReplayMiss, UpstreamError
from app.db.models import LlmCacheRow
from app.integrations.llm.base import LLMProvider, M, ModelTier


def cache_key(task: str, model: str, prompt: str, tier: ModelTier, schema: dict) -> str:
    payload = json.dumps([task, model, tier, prompt, schema], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


class TextResponse(BaseModel):
    text: str


class RecordingLLM:
    def __init__(
        self, inner: LLMProvider, mode: ProviderMode, fixtures_dir: Path, db: Session | None = None
    ) -> None:
        self.name = f"{inner.name}+{mode}"
        self._inner = inner
        self._mode = mode
        self._fixtures_dir = fixtures_dir / "llm"
        self._db = db

    def model_for(self, tier: ModelTier) -> str:
        return self._inner.model_for(tier)

    def generate_structured(
        self, *, task: str, prompt: str, schema: type[M], tier: ModelTier = ModelTier.REASONING
    ) -> M:
        return self._generate(task, prompt, schema, tier)

    def generate_text(
        self, *, task: str, prompt: str, tier: ModelTier = ModelTier.REASONING
    ) -> str:
        return self._generate(task, prompt, TextResponse, tier).text

    def _generate(self, task: str, prompt: str, schema: type[M], tier: ModelTier) -> M:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", task):
            raise ValueError("LLM task must be a simple task name")
        model = self.model_for(tier)
        key = cache_key(task, model, prompt, tier, schema.model_json_schema())
        path = self._fixtures_dir / task / f"{key}.json"
        if self._mode is ProviderMode.REPLAY:
            if not path.is_file():
                raise ReplayMiss(
                    f"No recorded LLM response for {task}. Record it once with LLM_MODE=record.",
                    details={"task": task, "key": key},
                )
            try:
                fixture = json.loads(path.read_text(encoding="utf-8"))
                if fixture["key"] != key or fixture["model"] != model:
                    raise ValueError("fixture metadata does not match request")
                return schema.model_validate(fixture["response"])
            except (ValueError, KeyError, TypeError) as exc:
                raise UpstreamError(f"Invalid recorded LLM response for {task}.") from exc

        row = self._db.get(LlmCacheRow, key) if self._db is not None else None
        result = None
        if row is not None:
            with suppress(ValidationError):
                result = schema.model_validate(row.response)
        if result is None:
            if schema is TextResponse:
                result = schema.model_validate(
                    {"text": self._inner.generate_text(task=task, prompt=prompt, tier=tier)}
                )
            else:
                result = self._inner.generate_structured(
                    task=task, prompt=prompt, schema=schema, tier=tier
                )
                result = schema.model_validate(result.model_dump())
            if self._db is not None:
                if row is None:
                    row = LlmCacheRow(key=key, task=task, model=model)
                    self._db.add(row)
                row.response = result.model_dump(mode="json")
                self._db.commit()
        if self._mode is ProviderMode.RECORD:
            fixture = {
                "key": key,
                "task": task,
                "model": model,
                "tier": tier,
                "response": result.model_dump(mode="json"),
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary.replace(path)
        return result
