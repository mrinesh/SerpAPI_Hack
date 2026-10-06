# 0018. Suggest the target ROI from the market's sourced typical value

- **Status:** Accepted
- **Date:** 2026-10-06

## Context

Investors typed a target ROI with no guidance. A target far from what the market gives makes
`meets_target_roi` meaningless: every candidate either fails or passes. The product owner asked
for a reasonable target to be filled in, which the investor can change. The suggestion must be
sourced (ADR 0008), so no number comes from the model's memory. For growth-based goals the
past-12-month figure (+29% Whitefield, +26.9% Koramangala) is one boom year and would make a
poor target; the same recorded results also quote multi-year changes.

## Decision

- **`POST /api/profiles/target-suggestion`** takes the segment, types, localities, goal and risk
  appetite. The wizard knows all of these by its Money step.
- **The typical value of the goal's measure** (ADR 0010) is computed in code for each locality
  and type:
  - **Rental yield:** area rent per sq ft per month × 12 ÷ area price per sq ft (ADR 0014,
    0017).
  - **Price growth:** the yearly rate from a multi-year change, (1 + total)^(1/years) − 1. It
    comes from the F-05 growth search, read by a new lite task `extract_long_run_growth`. Code
    checks that the span quotes the "%" figure and a 2–10 year period, and that its direction
    matches the sign.
  - **Total return:** both added.
- **Data sources:** values already cached in `area_intel` are used first. Otherwise the
  pipeline's own lookups run, and they are cached by the gateway and `llm_cache`.
- **Several localities or types:** the median.
- **Risk adjustment:** conservative × 0.9, balanced × 1.0, aggressive × 1.15. A target is then
  a little below or above what the market typically gives. Rounded to the nearest 0.5%, with a
  minimum of 0.5%.
- **No data** means no suggestion, and the hint asks the investor for their own target.
- **The wizard fills the field** only when it is empty or still holds the previous suggestion.
  An investor's own value, or a saved profile's, is never overwritten. The hint shows the basis
  and source links.
- **The demo profiles use the suggestion:** Whitefield 3%, Koramangala 6%. A test checks they
  still match the endpoint.

## Consequences

- **Recorded suggestions:**
  - Whitefield flats: 3.2% typical yield, suggested 3%. Growth: "96% over three years", 25.1% a
    year.
  - Koramangala offices: 5.8% typical yield, suggested 6%. Growth: "+92.2% in last 5 years",
    14.0% a year.
- **Growth isn't by property type.** The growth search covers property in general, so
  Koramangala's figure comes from a page about houses.
- **Multi-year growth is used only for the target.** The investor's measured price growth stays
  the past 12 months (F-09), so appreciation targets set from a 3–5 year average are often met in
  a boom year.
- **Cost:** a new locality costs up to 3 searches and 3 lite calls the first time; repeat lookups
  are free. Changing a demo profile's target changes the verification and explanation prompts,
  so they must be re-recorded (about 31 calls).
