"""Prompt templates live next to this file as `<task>.md`, one per LLM task.

Templates use `str.format` placeholders. Keeping prompts in files (not inline strings) makes them
reviewable in diffs and lets `task` double as the cache and fixture namespace.
"""

from pathlib import Path

_DIR = Path(__file__).parent


def load_prompt(task: str) -> str:
    return (_DIR / f"{task}.md").read_text(encoding="utf-8")
