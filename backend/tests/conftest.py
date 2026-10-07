"""Test setup: an isolated SQLite file and replay mode, so tests never touch the network."""

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="realty-intel-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["SERPAPI_MODE"] = "replay"
os.environ["LLM_MODE"] = "replay"
os.environ["SERPAPI_API_KEY"] = ""
os.environ["DEEPSEEK_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402

# Settings ignore empty env vars, so the blank keys above would fall through to the developer's
# real keys in .env. Tests never read .env.
Settings.model_config["env_file"] = None

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """A test client on an empty database (tables are recreated on startup)."""
    from app.db import models  # noqa: F401  (registers tables before drop_all)

    Base.metadata.drop_all(engine)
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def db():
    """A session on an empty database."""
    from app.db import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()


# Record which committed fixtures the suite reads (scripts/check_fixtures.py).
from tests import fixture_usage  # noqa: E402

fixture_usage.install()


def pytest_sessionfinish(session, exitstatus):
    fixture_usage.write_report()
