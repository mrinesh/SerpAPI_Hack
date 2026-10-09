"""Spike S-02: how accurately are listing facts read from search snippets? Regex vs DeepSeek.

    uv run python scripts/s02_accuracy.py            # replay: committed recordings only
    uv run python scripts/s02_accuracy.py --record   # record missing DeepSeek calls (spends)
    uv run python scripts/s02_accuracy.py --regex-only  # the parsers alone; no LLM at all

Reads 20 hand-labelled snippet entries (fixtures/spikes/s02_labels.json) from the recorded S-01
searches and scores three ways of reading them, per field:
- regex: the cleaning parsers alone (what discovery produces before any LLM call);
- llm: `extract_listing` asked for every field, given the entry with no parsed facts;
- shipped: regex first, then `extract_listing` for the fields regex left empty (the pipeline).
Findings are written up in docs/spikes/S-02-extraction-accuracy.md.
"""

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parent.parent
LABELS = BACKEND / "fixtures" / "spikes" / "s02_labels.json"
FIELDS = ("price_inr", "price_per_sqft", "size_sqft", "bedrooms", "status")
LLM_FIELDS = ("price_inr", "size_sqft", "bedrooms", "status")  # price per sq ft is never asked
CONDITIONS = ("regex", "llm", "shipped")


@dataclass
class Tally:
    correct: int = 0
    wrong: int = 0  # a value that is not the labelled one
    missed: int = 0  # the entry states it, nothing was read
    spurious: int = 0  # the entry does not state it, a value was read anyway
    errors: list[str] = field(default_factory=list)

    @property
    def scored(self) -> int:
        return self.correct + self.wrong + self.missed + self.spurious


def expected(label: dict, name: str) -> list | None:
    """The accepted values for a field, or None when the entry does not state it."""
    value = label.get(name)
    if isinstance(value, dict):
        value = value["value"]
    if value is None:
        return None
    return value if isinstance(value, list) else [value]


def matches(found, accepted: list, tolerance: float) -> bool:
    for want in accepted:
        if isinstance(want, (int, float)) and isinstance(found, (int, float)):
            if abs(found - want) <= abs(want) * tolerance:
                return True
        elif str(found) == str(want):
            return True
    return False


def score(tally: Tally, label: dict, name: str, found, tolerance: float, where: str) -> None:
    found = getattr(found, "value", found)  # enums compare and print as their value
    accepted = expected(label, name)
    if accepted is None:
        if found is None:
            tally.correct += 1
        else:
            tally.spurious += 1
            tally.errors.append(f"{where} {name}: read {found!r}, not stated")
    elif found is None:
        tally.missed += 1
        tally.errors.append(f"{where} {name}: missed {accepted[0]!r}")
    elif matches(found, accepted, tolerance):
        tally.correct += 1
    else:
        tally.wrong += 1
        tally.errors.append(f"{where} {name}: read {found!r}, expected {accepted[0]!r}")


def entry_listing(label: dict, market, settings):
    """The frozen pre-F-22 candidate used by this historical comparison.
    New parser regressions are checked separately, without changing old LLM request keys."""
    from app.schemas.listing import Listing

    baseline = json.loads(
        (BACKEND / "fixtures/spikes/s02_baseline.json").read_text(encoding="utf-8")
    )
    return Listing.model_validate(
        baseline[f"{label['fixture']}:{label['position']}:{label['entry']}"]
    )


def current_entry_listing(label: dict, market, settings):
    """The candidate the current parser builds, from the recorded search."""
    from app.pipeline.cleaning import is_rental_page, normalize_hits, snippet_entries
    from app.reference.localities import named_slugs
    from app.schemas.common import SerpEngine
    from app.schemas.listing import RawSearchHit

    recorded = json.loads(
        (settings.fixtures_dir / "serpapi" / "google" / f"{label['fixture']}.json").read_text(
            encoding="utf-8"
        )
    )
    query = recorded["params"]["q"]
    result = next(
        r for r in recorded["response"]["organic_results"] if r.get("position") == label["position"]
    )
    assert not is_rental_page(result.get("title", ""), result.get("link", ""))
    evidence = snippet_entries(result.get("snippet") or "")[label["entry"]].evidence
    slugs = named_slugs(query, market)
    hit = RawSearchHit(
        engine=SerpEngine.GOOGLE,
        query=query,
        locality=slugs[0] if slugs else "whitefield",
        property_type="office" if label["segment"] == "commercial" else "apartment",
        position=label["position"],
        title=result.get("title") or "",
        link=result.get("link"),
        snippet=result.get("snippet"),
        search_id=recorded["response"].get("search_metadata", {}).get("id"),
        fetched_at=datetime.now(UTC),
    )
    listings = normalize_hits(
        [hit], segment=label["segment"], market=market, now=datetime.now(UTC)
    ).listings
    return next(listing for listing in listings if listing.evidence == evidence)


def blank(listing):
    """The same entry with no parsed facts, so the LLM reads every field from the text alone."""
    from app.pipeline.verification import EXTRACT_FIELDS
    from app.schemas.provenance import ExtractionMethod, Sourced

    empty = listing.model_copy(deep=True)
    for name in (*EXTRACT_FIELDS, "price_per_sqft"):
        setattr(empty, name, Sourced(value=None, confidence=0, method=ExtractionMethod.REGEX))
    return empty


def measure(llm) -> tuple[dict[str, dict[str, Tally]], int, int]:
    """Scores every condition; with `llm` None, only the regex condition."""
    from app.config import get_settings
    from app.pipeline.verification import extract
    from app.reference import load_market

    settings = get_settings()
    market = load_market("Bengaluru")
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    tolerance = labels["tolerance_pct"] / 100
    ctx = SimpleNamespace(llm=llm)
    tallies = {c: {name: Tally() for name in FIELDS} for c in CONDITIONS}
    listings = non_listings = 0
    for label in labels["entries"]:
        where = f"{label['fixture'][:8]}#{label['position']}.{label['entry']}"
        if label["kind"] != "listing":
            non_listings += 1  # every condition reads it as a listing: cleaning has no filter
            continue
        listings += 1
        regex = entry_listing(label, market, settings)
        read = {"regex": regex}
        if llm is not None:
            read |= {"llm": extract(ctx, blank(regex)), "shipped": extract(ctx, regex)}
        for condition, listing in read.items():
            names = FIELDS if condition == "regex" else LLM_FIELDS
            for name in names:
                found = getattr(listing, name).value
                score(tallies[condition][name], label, name, found, tolerance, where)
    return tallies, listings, non_listings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--record", action="store_true", help="record missing DeepSeek calls")
    parser.add_argument("--regex-only", action="store_true", help="score the parsers alone")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="s02-") as temporary:
        os.environ["DATABASE_URL"] = f"sqlite:///{(Path(temporary) / 's02.db').as_posix()}"
        os.environ["LLM_MODE"] = "record" if args.record else "replay"
        from app.config import get_settings
        from app.integrations.llm.factory import get_llm

        settings = get_settings()
        if args.record and not settings.deepseek_api_key:
            sys.exit("DEEPSEEK_API_KEY is not configured.")
        tallies, listings, non_listings = measure(None if args.regex_only else get_llm(settings))
    print(f"{listings} listings and {non_listings} non-listing entries labelled\n")
    print(f"{'field':16}" + "".join(f"{c:>22}" for c in CONDITIONS))
    for name in FIELDS:
        cells = []
        for condition in CONDITIONS:
            tally = tallies[condition][name]
            cells.append(
                f"{tally.correct}/{tally.scored} ({tally.wrong}w {tally.missed}m {tally.spurious}s)"
                if tally.scored
                else "not asked"
            )
        print(f"{name:16}" + "".join(f"{cell:>22}" for cell in cells))
    for condition in CONDITIONS:
        errors = [e for name in FIELDS for e in tallies[condition][name].errors]
        if errors:
            print(f"\n{condition} errors:")
            for error in errors:
                print(f"  {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
