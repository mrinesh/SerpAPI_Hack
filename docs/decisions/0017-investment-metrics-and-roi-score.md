# 0017. Rental yield from a quoted area rent; a proportional ROI score

- **Status:** Accepted
- **Date:** 2026-10-06
- **Amends:** [0015](0015-composite-ranking.md) (fills its `roi` component)

## Context

ADR 0010 defined the ROI measures: rental yield before costs, price growth, and total return,
with the goal choosing which one is compared with the investor's target. Price growth exists
(F-05). Rent does not: the recorded Whitefield searches have no flat rents. Rent results quote
a monthly rent next to a size ("₹38,000 / month … 850 sqft"), and rarely a per-sq-ft rate. Both
demo profiles have a rental-income goal and, at the time, a 4% target (later 3% and 6%, the
suggested targets of ADR 0018).

## Decision

- **Rent level per locality and property type**, cached in the area like price levels:
  one Google search ("flat rent per sq ft in Whitefield Bangalore"). DeepSeek lite
  (`extract_rent`) lists every quoted rent and size pair with its exact span. Code checks each
  pair: the span is in the snippet, it quotes both numbers (₹, lakh and k forms), the result is
  a rent listing, and it is not a plot, seat, desk or daily rate. Rent ÷ size is computed in
  code, and the level is the **median of at least 3 checked pairs**. There is no fallback rate;
  too few pairs means no yield.
- **Yield without a unit size:** rent per sq ft per month × 12 ÷ the listing's sale price per sq
  ft × 100. Monthly rent in ₹ is shown only when the size is known.
- **No yield for a price flagged too good to be true.** A ₹75/sq ft "sale" would otherwise show
  an implausible yield.
- **Growth:** the profile's `expected_growth_pct` when set, else the area's past-12-month figure.
  Total return needs both yield and growth.
- **ROI points** = the goal's measure ÷ (1.5 × target) × 100, clamped to 0–100: 66.7 at the
  target and full marks at 1.5× it. A missing measure leaves `roi` null and the rest
  renormalised. **A missed target lowers the score but never filters or caps a candidate**,
  because the rent is an area estimate and not the unit's actual rent.

## Consequences

- **Recorded demos:**
  - Whitefield flats: ₹32.5/sq ft/month, the median of 5 pairs. Sowparnika Columns
    (₹8,185/sq ft) yields 4.76% and meets 4%; the ₹76 L flat (₹10,340/sq ft) yields 3.77% and is
    below it.
  - Koramangala offices: ₹84.4/sq ft/month, the median of 4 pairs; yields 6.4–7.2%. The
    flagged ₹3.6 L office has no yield.
- **Yields are likely high.** Listed rents can include maintenance or furnishing, rent searches
  mix unit types (a 2 BHK house and a 1 RK flat appeared among Whitefield flats), and asking
  prices are not sale prices. The UI says "before costs" and "estimated" wherever it shows yield.
- **Cost:** one rent search and one lite call per locality and type, per area TTL. Changing the
  ROI curve changes the explanation inputs, so the demo explanations must then be re-recorded
  (about 9 lite calls).
