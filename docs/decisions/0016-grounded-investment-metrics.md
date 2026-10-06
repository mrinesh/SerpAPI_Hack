# 0016. Comparable rent inputs, code arithmetic and frozen financial comparisons

- **Status:** Accepted
- **Date:** 2026-10-06
- **Extends:** [0010](0010-roi-definition.md), [0014](0014-locality-price-level.md)

## Context

F-03 determines relevance and F-05 explains the locality, but neither compares the financial
inputs to the investor's target. Search snippets are incomplete: a rent can be a deposit,
an annual rate, a seat price, or a quote for a different unit. The demo's inexpensive office
"sale" is likely a rent and must not yield a spectacular investment return.

## Decision

- Search rent once per locality/property type/BHK cohort. When housing BHK is unknown,
  require size and an explicit monthly rent rate per sq ft; do not guess BHK from size.
- Commercial monthly rent may be a per-sq-ft rate, or a whole-unit monthly amount with exactly
  one quoted sq-ft size. Code converts the latter to a rate and scales it to the candidate.
  These are indicative asking-rent estimates, not achieved rent or an appraisal. Lease terms,
  area definitions and fit-out can differ. Confidence is capped at 0.6.
- Deterministically screen rent snippets before DeepSeek chooses a complete snippet. Validate
  exact quote, locality, type, BHK/units, currency and amounts afterward too. Missing rent stays
  missing. A failed provider call retains its error code and recording instructions in the note.
- Search reported annual sale-price change once per locality/type. Reject quarterly/five-year
  changes, rental growth, forecasts and ambiguous percentages. A signed "changed by" figure is
  a reported change. Preserve the period and source date in the note; do not present past growth
  as a future estimate. The profile override takes precedence, including zero and negative values.
- Arithmetic is pure Python and carries the union of input sources and weakest confidence.
  Compare the selected goal measure at full precision; round only display values, except integer
  monthly rupees. Missing components never become zero. No invented costs, net yield or cap rate.
- Withhold price-dependent figures and ROI verdicts for unchecked/rejected candidates, starting
  or range prices, and implausibly cheap quotes. The profile target and unknown-assessment reason
  are part of the metric snapshot.
- Append `metrics` to existing `run_results` JSON one candidate at a time; preserve verification.
  A read-only metrics endpoint serves old or partial runs without external calls or schema migration.
  F-04 ranking and F-07 details remain separate features.

## Consequences

Users can compare quoted prices against same-type area levels and examine estimated gross yield
against their goal. Old comparisons remain reproducible after profile/listing changes. Different
layouts or incomplete search data can still prevent an ROI assessment; this is exposed explicitly.
Requests share gateway caches and obey existing search budgets. Replay demos cost no searches.
