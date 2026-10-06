# 0020. Locality news, shown but not scored; frozen per-run area evidence

- **Status:** Accepted
- **Date:** 2026-10-07
- **Amends:** [0016](0016-area-intelligence-and-score.md)
- **Credit:** adapted from gscode007's parallel `f-05` branch (their ADR 0015 there), including
  their recorded Google News fixtures for both demo localities.

## Context

F-05's news part was deferred. The teammate's branch implemented news with topic and sentiment
labels, and had recorded Google News for Whitefield and Koramangala. Our `engines.google_news()`
builds the same parameters, so those recordings replay unchanged here. Separately, a run's area
panel read the shared `area_intel` cache, so an old run's evidence changed after every refresh.
That breaks the per-run snapshot rule of ADR 0013, which listings, verifications and metrics
already follow.

## Decision

- **A sixth area search per locality:** Google News for `"<locality>" Bengaluru`.
- **News items are kept** when their own title or snippet names the locality (name or alias):
  - a story group (`highlight` + `stories`) contributes one article;
  - differently worded reports of one event are kept once, when at least half their meaningful
    words match;
  - URLs (without fragments) and titles are de-duplicated, and malformed items are skipped;
  - the 10 newest are kept, newest first.
- **DeepSeek lite (`classify_news`) labels** each item's topic (infrastructure, market, policy,
  civic, other) and sentiment, from its title and snippet only. Code requires every index
  exactly once; otherwise the `classify_news` section fails with a warning, and the news is shown
  without labels.
- **Display only, by the product owner's decision.** News does not enter the score, the ranking,
  the AI summary or the explanations. It is shown in the area panel: infrastructure first, then
  newest, with a note that headlines are as published and a planned project is not a completed
  one.
- **Frozen per-run areas:** the enrich stage saves the area each run used, with its merged price
  and rent levels, in a new `run_area_intel` table. `GET /api/runs/{id}/areas` serves these
  frozen copies, falling back to the shared cache only for runs created before this change.
  Deleting a profile deletes its runs' frozen areas.
- `AREA_SCHEMA_VERSION` goes to 3, so cached areas without news are rebuilt (free in replay).

## Consequences

- **The recorded demo results are unchanged** (ranks, scores, reasons, metrics), checked
  against a snapshot taken before the change.
- **Spend:** 2 DeepSeek lite calls; the news searches reuse the teammate's recordings.
- **A new locality** now costs 6 searches and 3 lite calls per TTL.
- **Some near-duplicates remain:** three reports of one Koramangala waste centre are worded too
  differently to match. Labels are AI judgements on headlines; for example, a metro-extension
  contract was labelled neutral.
- **Frozen copies take a row per run and locality**, which is small for this app's scale.
