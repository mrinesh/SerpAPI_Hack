"""Builds the LLM provider the rest of the app uses."""

from app.config import Settings
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.deepseek import DeepSeekProvider
from app.integrations.llm.recorder import RecordingLLM


def get_llm(settings: Settings) -> LLMProvider:
    return RecordingLLM(DeepSeekProvider(settings), settings.llm_mode, settings.fixtures_dir)
