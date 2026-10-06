# 0014. Flag implausible prices against a sourced, per-locality price level

- **Status:** Accepted
- **Date:** 2026-10-06

## Context

Portal snippets sometimes quote a rent as a sale price. S-01's Koramangala office ("₹3.6 Lac …
₹75 /sqft … 4,800 sqft") passed F-03 verification as a partial match within budget. A flat
floor (₹1,000/sq ft, say) was proposed and rejected: rates differ several-fold between
localities and between flats and offices, so one number is either too loose or too strict.
Asking DeepSeek for a typical rate from memory was also rejected: the number would be unsourced
and possibly out of date, and ADR 0008 lets the LLM extract numbers, never supply them.
"Price = rate × size" is no test either: it holds for every listing.

## Decision

- **Benchmark per locality and property type** (`pipeline/enrichment/price_level.py`): one
  Google search, `"<type words> price per sq ft in <locality> Bangalore"`. DeepSeek (lite,
  prompt `extract_price_level`) returns a sale rate, or a low–high range, from one result, with
  the exact span. Code checks that the span is in that snippet, quotes every returned number,
  says "sq ft", and has no rent, monthly, lease, yield or EMI wording. The midpoint is computed in
  code. The result is `Sourced` with the result's link and the search id.
- **Fallback:** the median of at least 3 per-sq-ft rates quoted on portal pages in the same run,
  locality and type. Otherwise there is no benchmark and no price flag. There is no flat rate.
- **Flag:** `too_good_to_be_true` (high) when a listing's rate is under 40% of the benchmark.
  The candidate stays in results, capped at **weak** (score ≤ 59), with the reason in its
  mismatches. Low prices are suspicious, not proven wrong. `missing_price` and `missing_size`
  are low-severity flags.
- **Flags never enter the verify prompt.** They are applied in code after the model, so changing
  a benchmark or threshold never invalidates recorded verifications.
- **No new cache:** the SerpApi cache and `llm_cache` already key on the exact request, so a
  locality costs 1 search and 1 lite call once per cache TTL.
- **Record mode serves existing fixtures first** (both gateways), so adding a new call to a
  recorded demo pays only for that call. Delete a fixture to refresh it.

## Consequences

The recorded demos flag only the ₹3.6 L office: ₹75/sq ft against Koramangala's
₹17,501/sq ft (0.4%). Whitefield's level is ₹12,150/sq ft (the midpoint of ₹11,700–12,600); its
cheapest in-budget flat quotes ₹5,073/sq ft, 42% of it, close to the threshold. The 40% share is
a judgement call to revisit with more localities. One portal's "average" can run high, because
it averages listed, not sold, prices. Each new locality costs one extra search per cache TTL.
