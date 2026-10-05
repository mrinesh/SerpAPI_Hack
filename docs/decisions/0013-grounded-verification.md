# 0013. Ground extraction and enforce hard profile constraints in code

- **Status:** Accepted
- **Date:** 2026-10-05

## Context

Discovery candidates contain sparse snippets and unpriced Maps projects. The model can confuse
page filters with facts, guess missing values or call an over-budget candidate a strong match.
Repeat runs update shared listings, but old verification must remain tied to the checked facts.

## Decision

- DeepSeek lite fills only null fields. Every added value needs an exact span from this
  candidate's evidence and a supported number/unit or enum word. Existing regex, computed,
  query and structured facts are preserved. No evidence means skip extraction.
- DeepSeek reasoning judges fit and free-text criteria. Application code checks segment,
  property type, locality, budget and requested size; confirmed violations force rejection
  and cap relevance at 39. This relevance score is distinct from F-04's composite ranking.
- Missing core facts and price ranges/starting prices prevent strong verdicts and cap
  relevance at 69 and confidence at 0.6. A starting-price lower bound cannot establish a
  minimum-budget violation. ROI stays unverified until investment metrics exist.
- The existing `run_results.recommendation` JSON is progressive: listing snapshot first,
  verification next, future recommendation fields at F-04. Rank stays null until F-04 and for
  rejects. This uses the existing table without resetting the database or search ledger.
- Each check commits independently. Failed runs keep discovery and completed checks.
- LLM cache keys include task/model/tier/schema/prompt. Prompts omit timestamps and profile
  ID/name. Replay uses fixtures exclusively, never silently falls back to a live call.

## Consequences

Hard constraints and extraction grounding are testable without live providers. Free-text
judgements still need live accuracy validation; existing search data cannot prove missing
facts. Tests create clearly fake temporary fixtures; none are shipped as live recordings.

**Per-run limit (2026-10-06).** Each candidate costs about two DeepSeek calls and ~30 s, so a
run checks at most `VERIFY_MAX_CANDIDATES` (default 16) in deterministic discovery order and
reports the rest as `unchecked`, not failed. This bounds live spend and lets the residential demo
(28 candidates, 16 recorded) succeed in replay. Unchecked candidates are shown but never ranked
as verified. Prompt files are read as `utf-8-sig`, because a BOM would change every cache key.
