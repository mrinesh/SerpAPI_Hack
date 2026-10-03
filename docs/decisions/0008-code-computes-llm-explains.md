# 0008. Code computes scores and money; the LLM extracts and explains

- **Status:** Accepted
- **Date:** 2026-10-03

## Context
LLM numeric output is not reproducible and is hard to audit. Investors need to trust yields and
rankings, and judges value engineering depth over prompt wrappers.

## Decision
- Deterministic code: price parsing (regex first), price per sq ft, yields, cap rate, quality
  flags, composite ranking score and its breakdown.
- LLM: classifying result kinds, extracting fields regex could not, judging fit against
  free-text criteria, classifying news, and writing reasons, summaries and market gaps.
- An LLM-written explanation may only quote numbers present in its inputs.

## Consequences
- Rankings are reproducible and explainable via `score_breakdown`.
- Metric and ranking code is unit-testable without any provider.
