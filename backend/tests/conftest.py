"""Test setup: an isolated SQLite file and replay mode, so tests never touch the network."""

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="realty-intel-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["SERPAPI_MODE"] = "replay"
os.environ["LLM_MODE"] = "replay"
os.environ["SERPAPI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as c:
        yield c
