# 0004. Every investor-facing fact carries source and confidence

- **Status:** Accepted
- **Date:** 2026-10-03

## Context
Extraction from search snippets can be wrong, and investors make money decisions on these numbers.
The brief calls for "a human-visible source link on every field".

## Decision
Investor-facing values are `Sourced[T]` (`app/schemas/provenance.py`): value, confidence,
extraction method (`serpapi_field`, `regex`, `llm`, `computed`), source references with the
SerpApi `search_id`, and an optional note. Computed values carry their inputs' sources forward.

## Consequences
- The UI can always answer "where did this come from?" (F-11).
- Schemas are more verbose, and every stage must thread sources through.
- Confidence lets ranking down-weight shaky data instead of trusting it blindly.
