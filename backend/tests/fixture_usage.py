"""Records which committed fixtures the test suite reads, so unused recordings can be found.

Loaded by `tests/conftest.py`. Both readers are wrapped for the whole session: the SerpApi
gateway's and the LLM recorder's `_read_fixture`. With `FIXTURE_REPORT=<path>` set, the paths
read (relative to `backend/fixtures/`) are written there as JSON at the end of the session;
`scripts/check_fixtures.py` compares them with what is on disk.
"""

import json
import os
from pathlib import Path

from app.config import get_settings
from app.integrations.llm.recorder import RecordingLLM
from app.integrations.serpapi.gateway import SerpApiGateway

USED: set[str] = set()


def install() -> None:
    root = get_settings().fixtures_dir
    read_serp = SerpApiGateway._read_fixture
    read_llm = RecordingLLM._read_fixture

    def note(path: Path) -> None:
        # Tests that record into a temporary folder are not reading committed fixtures.
        if path.resolve().is_relative_to(root.resolve()):
            USED.add(path.resolve().relative_to(root.resolve()).as_posix())

    def serp(self, engine, key):
        data = read_serp(self, engine, key)
        if data is not None:
            note(self._fixture_path(engine, key))
        return data

    def llm(path: Path, *args, **kwargs):
        result = read_llm(path, *args, **kwargs)
        note(path)
        return result

    SerpApiGateway._read_fixture = serp
    RecordingLLM._read_fixture = staticmethod(llm)


def write_report() -> None:
    target = os.environ.get("FIXTURE_REPORT")
    if target:
        Path(target).write_text(json.dumps(sorted(USED), indent=1), encoding="utf-8")
