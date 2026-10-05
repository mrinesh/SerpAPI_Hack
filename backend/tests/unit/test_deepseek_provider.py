"""DeepSeekProvider against a fake OpenAI client: request shape, tiers, validation and retry."""

from types import SimpleNamespace

import httpx2
import openai
import pytest
from pydantic import BaseModel

from app.config import Settings
from app.core.errors import ProviderNotConfigured, UpstreamError
from app.integrations.llm.base import ModelTier
from app.integrations.llm.deepseek import DeepSeekProvider


class Listing(BaseModel):
    bhk: int
    price_lakh: float


class FakeClient:
    """Mimics `client.chat.completions.create`; each reply is a content string or an exception."""

    def __init__(self, *replies: str | Exception | None) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **request):
        self.calls.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        message = SimpleNamespace(content=reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_provider(*replies, **overrides) -> tuple[DeepSeekProvider, FakeClient]:
    client = FakeClient(*replies)
    settings = Settings(
        _env_file=None,
        **{"deepseek_api_key": "test-key", "deepseek_model_lite": "lite-model", **overrides},
    )
    return DeepSeekProvider(settings, client_factory=lambda: client), client


def test_structured_validates_reply_in_json_mode():
    provider, client = make_provider('{"bhk": 3, "price_lakh": 120.0}')

    result = provider.generate_structured(task="extract_listing", prompt="3 BHK", schema=Listing)

    assert result == Listing(bhk=3, price_lakh=120.0)
    request = client.calls[0]
    assert request["response_format"] == {"type": "json_object"}
    assert request["model"] == "deepseek-v4-pro"
    system = request["messages"][0]["content"]
    assert "json" in system and '"price_lakh"' in system  # JSON mode needs "json" in the prompt


def test_tiers_pick_model_and_thinking():
    provider, client = make_provider("a", "b")

    provider.generate_text(task="t", prompt="p")
    provider.generate_text(task="t", prompt="p", tier=ModelTier.LITE)

    reasoning, lite = client.calls
    assert reasoning["model"] == "deepseek-v4-pro"
    assert reasoning["extra_body"] == {"thinking": {"type": "enabled"}}
    assert lite["model"] == "lite-model"
    assert lite["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "response_format" not in reasoning


@pytest.mark.parametrize("bad_reply", ['{"bhk": "three"}', "", None])
def test_structured_retries_once_with_the_error(bad_reply):
    provider, client = make_provider(bad_reply, '{"bhk": 2, "price_lakh": 85}')

    result = provider.generate_structured(task="t", prompt="p", schema=Listing)

    assert result.bhk == 2
    retry = client.calls[1]["messages"]
    assert retry[-2] == {"role": "assistant", "content": bad_reply or ""}
    assert retry[-1]["role"] == "user" and "not valid" in retry[-1]["content"]


def test_structured_gives_up_after_two_invalid_replies():
    provider, client = make_provider("{}", "{}")

    with pytest.raises(UpstreamError, match="invalid Listing"):
        provider.generate_structured(task="t", prompt="p", schema=Listing)
    assert len(client.calls) == 2


def test_empty_text_reply_is_an_upstream_error():
    provider, _ = make_provider("  ")

    with pytest.raises(UpstreamError, match="empty reply"):
        provider.generate_text(task="t", prompt="p")


def test_api_failure_maps_to_upstream_error():
    request = httpx2.Request("POST", "https://api.deepseek.com/chat/completions")
    provider, _ = make_provider(openai.APIConnectionError(request=request))

    with pytest.raises(UpstreamError, match="DeepSeek request"):
        provider.generate_text(task="t", prompt="p")


def test_missing_key_never_builds_a_client():
    provider, client = make_provider(deepseek_api_key=None)

    with pytest.raises(ProviderNotConfigured):
        provider.generate_text(task="t", prompt="p")
    assert client.calls == []
