# 0003. Record/replay providers and a hard search budget

- **Status:** Accepted
- **Date:** 2026-10-03

## Context
The free SerpApi tier is 250 searches a month, and a fresh pipeline run costs about 25. Judges
may not have SerpApi or Gemini keys. Tests must not touch the network.

## Decision
Both providers run in one of three modes, `live`, `record`, `replay`, defaulting to `replay`.
Record mode writes responses to `backend/fixtures/`, which are committed. Every SerpApi lookup
goes through one gateway that checks a DB cache, enforces per-run and monthly caps from a search
ledger, and handles record/replay. The fixture file name is the cache key.

## Consequences
- A fresh clone runs the full demo with no keys and no spend.
- `cache_key` must stay stable; changing it orphans every fixture (it has tests).
- New SerpApi or LLM calls need fixtures recorded before replay mode can serve them.
