"""Which of a market's localities a piece of text names (CHECKLIST I-12, ADR 0024).

Used by cleaning to confirm a listing's locality from its own text instead of trusting the
query that found it. Matching is on whole words after normalising case and punctuation, so
"Koramangala, Bengaluru" and "koramangala-8th-block" both name Koramangala:
- names and aliases from the market file (aliases only as observed in recorded results);
- spaced initials are joined, so "K R Puram" matches "KR Puram";
- one-word names of 8+ letters also match a word within a small edit distance
  ("Indiranagara", "Malleshwaram"), which short names would turn into false hits;
- a name followed by a landmark word ("Sarjapur Road", "Marathahalli Metro", "KR Puram
  Railway") is a place on the way, not the listing's locality, and does not count.
"""

import re

from rapidfuzz import fuzz

from app.reference import Locality, Market

LANDMARKS = {
    "road", "rd", "main", "metro", "station", "railway", "bus", "stand", "flyover", "junction",
    "signal", "circle", "lake", "highway", "bridge", "toll", "exit", "outer", "ring",
}  # fmt: skip
FUZZY_MIN_LETTERS = 8
FUZZY_MIN_RATIO = 90


def normalize(text: str) -> list[str]:
    """Lowercase words, punctuation dropped, runs of single letters joined ("K R Puram" ->
    ["kr", "puram"]), so spaced and unspaced initials compare equal."""
    joined: list[str] = []
    in_initials = False
    for word in re.sub(r"[^a-z0-9]+", " ", text.lower()).split():
        initial = len(word) == 1 and word.isalpha()
        if initial and in_initials:
            joined[-1] += word
        else:
            joined.append(word)
        in_initials = initial
    return joined


def named_localities(text: str | None, market: Market) -> list[Locality]:
    """The market's localities that `text` names as a place, in the market file's order."""
    if not text:
        return []
    words = normalize(text)
    return [place for place in market.localities if _names(words, place)]


def named_slugs(text: str | None, market: Market) -> list[str]:
    return [place.slug for place in named_localities(text, market)]


def _names(words: list[str], place: Locality) -> bool:
    for name in (place.name, *place.aliases):
        target = normalize(name)
        size = len(target)
        for start in range(len(words) - size + 1):
            window = words[start : start + size]
            if window == target or _close(window, target):
                following = words[start + size] if start + size < len(words) else ""
                if following not in LANDMARKS:
                    return True
    return False


def _close(window: list[str], target: list[str]) -> bool:
    return (
        len(target) == 1
        and len(target[0]) >= FUZZY_MIN_LETTERS
        and fuzz.ratio(window[0], target[0]) >= FUZZY_MIN_RATIO
    )
