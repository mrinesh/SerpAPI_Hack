"""LLM record/replay and database reuse, with no API keys or network."""

import json

import pytest
from pydantic import BaseModel

from app.config import ProviderMode
from app.core.errors import ReplayMiss, UpstreamError
from app.integrations.llm.base import ModelTier
from app.integrations.llm.recorder import RecordingLLM


class Answer(BaseModel):
    value: int


class Provider:
    name = "fake"
    calls = 0

    def model_for(self, tier):
        return "model"

    def generate_structured(self, **kwargs):
        self.calls += 1
        return kwargs["schema"](value=42)

    def generate_text(self, **kwargs):
        self.calls += 1
        return "A summary"


def call(llm, **overrides):
    return llm.generate_structured(
        **{"task": "test_task", "prompt": "json please", "schema": Answer, **overrides}
    )


def test_record_then_replay_and_live_database_cache(db, tmp_path):
    provider = Provider()
    live = RecordingLLM(provider, ProviderMode.LIVE, tmp_path, db)
    assert call(live).value == 42
    assert call(live).value == 42
    assert provider.calls == 1
    record = RecordingLLM(provider, ProviderMode.RECORD, tmp_path, db)
    assert call(record).value == 42
    assert provider.calls == 1  # record writes cached output too
    replay = RecordingLLM(provider, ProviderMode.REPLAY, tmp_path)
    assert call(replay).value == 42
    assert provider.calls == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"tier": ModelTier.LITE},
        {"prompt": "a different prompt"},
        {"task": "different_task"},
    ],
)
def test_changed_request_has_no_fixture(tmp_path, overrides):
    provider = Provider()
    call(RecordingLLM(provider, ProviderMode.RECORD, tmp_path))
    with pytest.raises(ReplayMiss):
        call(RecordingLLM(provider, ProviderMode.REPLAY, tmp_path), **overrides)
    assert provider.calls == 1


def test_replay_does_not_read_live_database_cache(db, tmp_path):
    provider = Provider()
    call(RecordingLLM(provider, ProviderMode.LIVE, tmp_path, db))
    with pytest.raises(ReplayMiss):
        call(RecordingLLM(provider, ProviderMode.REPLAY, tmp_path, db))
    assert provider.calls == 1


def test_invalid_recorded_output_is_reported(tmp_path):
    provider = Provider()
    call(RecordingLLM(provider, ProviderMode.RECORD, tmp_path))
    path = next(tmp_path.rglob("*.json"))
    payload = json.loads(path.read_text())
    payload["response"] = {"value": "invalid"}
    path.write_text(json.dumps(payload))
    with pytest.raises(UpstreamError, match="Invalid recorded"):
        call(RecordingLLM(provider, ProviderMode.REPLAY, tmp_path))
    assert provider.calls == 1


def test_text_record_replay(tmp_path):
    provider = Provider()
    record = RecordingLLM(provider, ProviderMode.RECORD, tmp_path)
    assert record.generate_text(task="summary", prompt="summarise") == "A summary"
    replay = RecordingLLM(provider, ProviderMode.REPLAY, tmp_path)
    assert replay.generate_text(task="summary", prompt="summarise") == "A summary"
    assert provider.calls == 1


def test_task_cannot_escape_fixture_directory(tmp_path):
    with pytest.raises(ValueError):
        call(RecordingLLM(Provider(), ProviderMode.REPLAY, tmp_path), task="../escape")
