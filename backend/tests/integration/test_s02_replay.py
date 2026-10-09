"""S-02 replays from its recordings and still gives the numbers in the spike write-up
(docs/spikes/S-02-extraction-accuracy.md)."""

import importlib.util
import json
from pathlib import Path

from app.config import get_settings
from app.integrations.llm.factory import get_llm
from app.reference import load_market

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "s02_accuracy.py"


def load_script():
    spec = importlib.util.spec_from_file_location("s02_accuracy", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def correct(tallies, condition):
    return {name: tally.correct for name, tally in tallies[condition].items() if tally.scored}


def test_s02_headline_numbers_replay():
    s02 = load_script()
    tallies, listings, non_listings = s02.measure(get_llm(get_settings()))
    assert (listings, non_listings) == (19, 1)
    assert correct(tallies, "regex") == {
        "price_inr": 19, "price_per_sqft": 19, "size_sqft": 18, "bedrooms": 19, "status": 18,
    }  # fmt: skip
    assert correct(tallies, "llm") == {
        "price_inr": 15, "size_sqft": 14, "bedrooms": 19, "status": 19,
    }  # fmt: skip
    assert correct(tallies, "shipped") == {
        "price_inr": 19, "size_sqft": 18, "bedrooms": 19, "status": 18,
    }  # fmt: skip
    # The LLM alone never states a wrong value; it misses what needs arithmetic.
    assert sum(t.wrong + t.spurious for t in tallies["llm"].values()) == 0


def test_current_parsers_correct_all_labelled_listing_fields():
    s02 = load_script()
    labels = json.loads(s02.LABELS.read_text(encoding="utf-8"))
    market = load_market("Bengaluru")
    for label in labels["entries"]:
        if label["kind"] != "listing":
            continue
        listing = s02.current_entry_listing(label, market, get_settings())
        for name in s02.FIELDS:
            found = getattr(listing, name).value
            accepted = s02.expected(label, name)
            assert (
                found is None
                if accepted is None
                else s02.matches(found, accepted, labels["tolerance_pct"] / 100)
            ), (label, name, found)
