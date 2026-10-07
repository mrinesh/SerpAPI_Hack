# 0017 — Measured search history drives locality research

Date: 2026-10-07 · Status: Accepted · F-05 P1

## Context

News and model explanations do not establish increasing property interest. The user requested
public search histories and actual app searches, growth observations, and AI-reviewed plausible
causes to guide developing-area recommendations.

## Decision

Collect Google Trends broad/rental histories in two batches of at most five queries, and
capture requested locality intents when a run starts. Aggregate app searches by distinct
profile per complete UTC week; preserve original locality choices rather than re-reading
edited profiles. Retain frozen per-run assessments in a separate table.

Use code for complete-week quarter/annual comparisons, persistence checks, corroboration,
transparent scores and research-priority ranks. Require property-related growth plus observed
price or recent news evidence. Keep missing data unavailable and exclude investor assumptions.
DeepSeek reviews consistency and selects complete cited news quotes for unconfirmed causal
hypotheses; it cannot change the numerical assessment. Validate indices/quotes/driver terms.

## Consequences

The UI can explain a result through measured histories and distinguish attention from
development evidence. Declining or insufficient histories can yield no priority. The app
needs months of real observations to contribute its own reliable baseline; public history
can be used immediately. Counts represent profiles, not people. Trends indexes are relative,
not absolute search volumes, and independent batches must not be compared by raw levels.
Two additional Trends searches share the existing budget/cache/recording infrastructure.
Thresholds and weights remain disclosed heuristics. Actual development and causation require
independent evidence; full property ranking remains F-04.

Details: [methodology, benefits and demo results](../SEARCH_DRIVEN_AREA_INSIGHTS.md).
