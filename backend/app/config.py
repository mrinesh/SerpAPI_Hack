"""Application settings, loaded from environment variables and `.env`.

Both external providers (SerpApi and the LLM) run in one of three modes so the app works
without network access or API keys. See docs/decisions/0003-record-replay-and-search-budget.md.
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class ProviderMode(StrEnum):
    LIVE = "live"  # call the real API; cache responses in the database
    RECORD = "record"  # live, and also write each response to fixtures/ for replay
    REPLAY = "replay"  # never touch the network; serve from fixtures/ only


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # `SERPAPI_API_KEY=` in .env means "not set"
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'realty_intel.db'}"
    cors_origins: list[str] = ["http://localhost:5173"]

    # SerpApi. Replay is the default so a fresh clone never spends search credits.
    serpapi_api_key: str | None = None
    serpapi_mode: ProviderMode = ProviderMode.REPLAY
    serpapi_monthly_budget: int = 250  # free tier
    serpapi_run_budget: int = 40  # hard cap on live searches per pipeline run
    serpapi_cache_ttl_hours: int = 72
    serpapi_timeout_s: int = 30

    # LLM (Gemini). `gemini_model` reasons and scores; `gemini_model_lite` does bulk extraction.
    gemini_api_key: str | None = None
    llm_mode: ProviderMode = ProviderMode.REPLAY
    gemini_model: str = "gemini-3.8-flash"
    gemini_model_lite: str = "gemini-3.5-flash-lite"

    # Market defaults. Bengaluru is the demo market; nothing in the pipeline is city-specific.
    default_city: str = "Bengaluru"
    serpapi_location: str = "Bengaluru,Karnataka,India"  # SerpApi `location` parameter
    serpapi_gl: str = "in"
    serpapi_hl: str = "en"
    serpapi_google_domain: str = "google.co.in"

    # Enrichment results are shared per locality, so they can live longer than search caches.
    area_intel_ttl_hours: int = 168

    # Background jobs (alerts, scheduled refresh). Off by default for local runs.
    scheduler_enabled: bool = False
    alert_check_interval_minutes: int = 360

    fixtures_dir: Path = BACKEND_DIR / "fixtures"


@lru_cache
def get_settings() -> Settings:
    return Settings()
