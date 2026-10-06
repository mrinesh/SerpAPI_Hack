# 0015. Area evidence, partial failures and run snapshots

- **Status:** Accepted
- **Date:** 2026-10-06

## Context

F-05 extends the locality cache in ADR 0006. Maps results can be ambiguous, News can be unrelated,
and provider/fixture failures must not masquerade as empty data. Later ranking needs the exact
area evidence used by a run, even after the shared cache changes.

## Decision

- Resolve known locality names/aliases against market reference data. Do not guess geography.
- Reuse `area_intel`, SerpApi/LLM gateways and their fixtures. Complete payloads use the configured
  TTL; partial payloads expire immediately. Validate schema version/provider modes before reuse.
  Record mode bypasses only the derived cache so raw recordings can be completed.
- Maps amenity categories require provider place types; distances are calculated from sourced
  coordinates. News requires locality evidence in its own title/snippet.
- Keep raw normalized news. DeepSeek labels topics/sentiment and selects infrastructure evidence;
  code accepts only complete titles/snippets tied to an input index. Summaries join those quotes.
- Expected provider failures become typed section warnings; unexpected internal failures still
  fail the run. Read-only GET endpoints never spend credits.
- Commit an immutable `run_area_intel` snapshot per run/locality. Attach already computed price
  benchmarks there; the shared cache excludes run-specific property types.

## Alternatives and consequences

Automatic GET refresh would create untracked paid searches. Free-form generated prose would be
harder to validate. Reading the latest cache for old runs would change their evidence. Separate
cache/fixture infrastructure would duplicate existing abstractions. These alternatives were
rejected in favor of the smaller extension above.

Costs scale with discovered localities: up to five searches and two LLM calls per uncached area.
Conservative matching can omit useful data. Partial areas require inspecting warnings, not just
the run's overall status. Existing runs have no new snapshots until rerun. F-09/F-04 can consume
consistent sourced area payloads without implementing another external provider layer.

Implementation, code walkthrough and debugging: [F-05 guide](../F05_AREA_INTELLIGENCE.md).
