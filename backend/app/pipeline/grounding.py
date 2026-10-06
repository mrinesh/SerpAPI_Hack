"""The number check on LLM-written text (ADR 0008): text may quote only numbers it was given.

Used by recommendation explanations (F-04, ADR 0015) and area summaries (F-05, ADR 0016).
"""

import re

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> set[str]:
    return {_canonical(match) for match in _NUMBER.findall(text)}


def allowed_numbers(figures: dict[str, str] | list[str]) -> set[str]:
    values = figures.values() if isinstance(figures, dict) else figures
    return set().union(*(numbers_in(value) for value in values))


def grounded(text: str, allowed: set[str]) -> bool:
    """True when every number in `text` appears among the figures the model was given."""
    return numbers_in(text) <= allowed


def _canonical(number: str) -> str:
    text = number.replace(",", "")
    return text.rstrip("0").rstrip(".") if "." in text else text
