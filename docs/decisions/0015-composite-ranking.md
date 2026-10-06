# 0015. Composite ranking in code, with grounded explanations for the top five

- **Status:** Accepted
- **Date:** 2026-10-06

## Context

F-04 turns verified candidates into a ranked shortlist. ADR 0008 requires scores to be computed
in code and the LLM to only explain. Two planned inputs do not exist yet: ROI against the
target (F-09) and area signals (F-05). The F-03 relevance scores cluster between 60 and 70, so
relevance alone does not separate candidates well.

## Decision

- **Five components, each 0–100.** `relevance` is the F-03 match score. `value` is
  `50 + (1 − rate ÷ area level) × 125`, clamped; it is 50 at the locality price level (ADR 0014)
  and 100 at 0.6× of it. `evidence` is half verification confidence, half the share of price,
  size and status present. `roi` (F-09) and `area` (F-05) are not available yet.
- **Weights by goal** (percentage points: relevance, roi, value, evidence, area):
  rental income 40/25/15/15/5, appreciation 35/20/25/10/10, balanced 40/20/20/12/8.
  Conservative investors move 5 points from relevance and 5 from value to evidence; aggressive
  investors move 5 from evidence to value. Every weight stays above zero.
- **Unavailable components are left out** and the remaining weights are renormalised. This
  applies both to ROI and area signals for every candidate, and to `value` for a candidate with
  no rate or no area level. `score_breakdown` gives each component's points, or `null`.
- **Penalty:** −25 points per high-severity flag. A candidate flagged too good to be true also
  gets no `value` points, because a suspicious bargain must not score as value.
- **Ranking:** every checked, non-rejected candidate, by score, then lower price, then id.
  Rejected and unchecked candidates keep rank `null`.
- **Reasons:** each ranked candidate gets a deterministic reason written by code. The top 5
  also get a DeepSeek-written reason, highlights and risks (lite tier, `explain_recommendation`).
  The model is given pre-formatted display figures, and code checks every number it writes
  against them. A reason that fails falls back to the code reason; a highlight or risk that fails
  is dropped. `explained` records which reasons are AI-written.
- Scores and code reasons are saved before any explanation call, so a provider failure fails the
  stage but keeps the ranking.

## Consequences

The recorded demos rank 12 residential and 4 commercial candidates. The ₹3.6 L office flagged
as a likely rent ranks last of the 4. All 9 recorded explanations pass the number check. The
check catches invented numbers but not a mislabelled real one: one explanation called a
listing's own ₹15,853/sq ft "an area rate". When F-09 and F-05 land, their components fill in
`roi` and `area` without changing the formula. Changing weights changes the explanation prompts'
inputs (rank and score figures), so the demo explanations must then be re-recorded: about
9 lite calls.
