# 0023. Competitors per locality and business type, read by property type, not scored

- **Status:** Accepted
- **Date:** 2026-10-07
- **Builds on:** [0006](0006-locality-keyed-enrichment.md), [0019](0019-visible-failures-validated-cache-withheld-metrics.md), [0020](0020-local-news-and-frozen-run-areas.md), [0022](0022-map-positions-only-from-serpapi.md)

## Context

F-06 shows a commercial investor the same-category businesses around a property. Commercial
candidates are portal search-page snippets with no GPS (S-01), so there is no property point to
search around. The commercial demo is an office for an "IT services" business: for an office
buyer, nearby IT firms are mostly a sign of a business district and tenant demand, while for a
shop the same count would mean competition. The recorded search ("IT services" at the
Koramangala centre, zoom 15) returned one page of 20 places, 7 within 2 km and the rest 2.3 to
5.6 km away in BTM, Jayanagar, HSR and Domlur, with a further page available.

## Decision

- **One report per locality and business type**, centred on the area's geocoded centre (F-05),
  cached in `competitor_reports` for the area TTL, keyed by locality, rounded centre, business
  type (case and spacing ignored) and radius. One google_maps search per commercial locality.
- **Places within 2 km** of the centre count; farther ones are dropped. Distances, density,
  average rating (rated places only) and total reviews are computed in code; no LLM is used.
- **Density level** from the count within the radius, out of one page of 20: 10 or more is
  high, 4 to 9 medium, fewer low. The UI says the count comes from the first page and is a floor
  when Google has more.
- **Reading by property type** (`READINGS`): `shop_showroom` is *competition*; `office`,
  `warehouse` and `commercial_land` are a *business cluster*. Readings are recomputed for each
  profile, never taken from the cache. The wording is cautious: a signal to check, not a verdict.
- **Display only**: the report does not change the score, the ranking or the AI explanations
  (as with news, ADR 0020). A test runs the commercial demo with and without it and compares the
  shortlist.
- **Frozen per run** in `run_competitor_reports`, like areas; the detail page reads the run's
  report for the listing's locality, and its places join "Where this came from" (F-11).
- **Failures are visible** (ADR 0019): a failed search gives a `failed` report with the error,
  which expires at once so the next run retries; it never fails the run. No centre means no
  report, noted in the enrich stage message.

## Consequences

- The commercial demo shows "Business cluster: medium" from 7 places, at the cost of 1 search.
- Thresholds are judgement calls on a 20-place sample; they are constants in
  `enrichment/competitors.py` and can be tuned with more recordings.
- F-06b (review gaps from google_maps_reviews, P1) can use each place's stored `data_id` without
  a new search for the places themselves.
