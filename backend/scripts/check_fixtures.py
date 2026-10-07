"""Find committed recordings that nothing uses, so the fixture set stays clean.

    uv run python scripts/check_fixtures.py           # report; exit 1 on unused LLM fixtures
    uv run python scripts/check_fixtures.py --prune   # also delete unused LLM fixtures

Runs the test suite with `FIXTURE_REPORT` set (tests/fixture_usage.py records every fixture the
gateway and the LLM recorder read). A fixture also counts as used when a test or script names
its file, e.g. a test that parses a recorded response directly.

- LLM recordings (`fixtures/llm/`) that nothing uses are orphans, typically superseded by a
  re-recording after a prompt or input change. They fail the check and `--prune` deletes them.
- SerpApi recordings (`fixtures/serpapi/`) cost a search each and double as spike evidence
  (S-01), so unused ones are only reported, never deleted.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
FIXTURES = BACKEND / "fixtures"
SOURCES = [BACKEND / "tests", BACKEND / "scripts"]


def used_by_tests() -> set[str]:
    with tempfile.TemporaryDirectory(prefix="fixture-report-") as temporary:
        report = Path(temporary) / "used.json"
        env = {**os.environ, "FIXTURE_REPORT": str(report)}
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=BACKEND,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout[-3000:], result.stderr[-2000:], sep="\n")
            sys.exit("The test suite failed; fix it before checking fixtures.")
        return set(json.loads(report.read_text(encoding="utf-8")))


def named_in_sources() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for folder in SOURCES
        for path in folder.rglob("*.py")
        if path.name != Path(__file__).name
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prune", action="store_true", help="delete unused LLM fixtures")
    args = parser.parse_args()

    used = used_by_tests()
    sources = named_in_sources()

    def unused(kind: str) -> list[Path]:
        return sorted(
            path
            for path in (FIXTURES / kind).rglob("*.json")
            if path.relative_to(FIXTURES).as_posix() not in used and path.stem not in sources
        )

    llm, serp = unused("llm"), unused("serpapi")
    total_llm = len(list((FIXTURES / "llm").rglob("*.json")))
    total_serp = len(list((FIXTURES / "serpapi").rglob("*.json")))
    print(f"LLM fixtures: {total_llm - len(llm)} of {total_llm} used")
    print(f"SerpApi fixtures: {total_serp - len(serp)} of {total_serp} used by tests")
    if serp:
        print("SerpApi fixtures not used by tests (kept: each cost a search; S-01 evidence):")
        for path in serp:
            print(f"  {path.relative_to(FIXTURES)}")
    if llm:
        print("Unused LLM fixtures (superseded recordings):")
        for path in llm:
            print(f"  {path.relative_to(FIXTURES)}")
        if args.prune:
            for path in llm:
                path.unlink()
            print(f"Deleted {len(llm)}.")
            return 0
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
