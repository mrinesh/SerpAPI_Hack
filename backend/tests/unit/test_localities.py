"""Locality matching: which localities a piece of text names (I-12, ADR 0024). Example
phrases are spellings observed in the recorded S-01 results."""

import pytest

from app.reference import load_market
from app.reference.localities import named_slugs, normalize

MARKET = load_market("Bengaluru")


def test_normalize_joins_spaced_initials_only():
    assert normalize("K R Puram, Bengaluru") == ["kr", "puram", "bengaluru"]
    assert normalize("is a flat") == ["is", "a", "flat"]  # "is" is not an initial
    assert normalize("koramangala-8th-block") == ["koramangala", "8th", "block"]


@pytest.mark.parametrize(
    ("text", "slugs"),
    [
        ("3 BHK Flat for sale in Whitefield", ["whitefield"]),
        ("4th Block, Koramangala, Bengaluru, Karnataka 560095", ["koramangala"]),
        ("Office in K R Puram", ["kr-puram"]),  # spaced initials
        ("Flats in Indira Nagar", ["indiranagar"]),  # observed alias
        ("near Indiranagara 2nd stage", ["indiranagar"]),  # close spelling, long name
        ("Jp Nagar Phase 7", ["jp-nagar"]),
        ("Jaya Nagar 1st Block", ["jayanagar"]),
        ("HSR Layout sector 2", ["hsr-layout"]),
        ("Flat in Hoodi, Kadugodi", []),  # not reference localities
        ("", []),
    ],
)
def test_named_localities(text, slugs):
    assert named_slugs(text, MARKET) == slugs


@pytest.mark.parametrize(
    "text",
    [
        "Villa on Sarjapur Road",
        "Whitefield Main Road, Hoodi",
        "2 km from Marathahalli Metro",
        "near KR Puram Railway Station",
        "opp. Hebbal Flyover",
    ],
)
def test_landmarks_do_not_name_a_locality(text):
    assert named_slugs(text, MARKET) == []


def test_short_names_need_an_exact_word():
    # Fuzzy matching is for names of 8+ letters; "Hebbala" must not become Hebbal.
    assert named_slugs("Hebbala village", MARKET) == []
    assert named_slugs("Hebbal, Bengaluru", MARKET) == ["hebbal"]
