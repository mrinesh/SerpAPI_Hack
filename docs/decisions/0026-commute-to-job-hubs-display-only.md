# 0026. Commute to job hubs from google_maps_directions, display only

- **Status:** Accepted
- **Date:** 2026-10-08
- **Builds on:** [0006](0006-locality-keyed-enrichment.md), [0016](0016-area-intelligence-and-score.md), [0019](0019-visible-failures-validated-cache-withheld-metrics.md), [0022](0022-map-positions-only-from-serpapi.md)

## Context

In Bengaluru, rental demand in a locality depends on how long the morning drive to the big
employment clusters takes. Investors ask questions like "Whitefield to Manyata at 9 AM?", and
the area card did not answer them. F-05 already geocodes each locality's centre and caches it
for 7 days. SerpApi's `google_maps_directions` engine takes `start_coords`, an `end_addr` and a
departure time. Spike [S-04](../spikes/S-04-commute-directions.md) found that its times are
traffic-aware, that Google reads the departure as local wall-clock time, and that a past date
still works.

## Decision

- **Three named job hubs per market**, in `bengaluru.json`: ORR (Bellandur), Manyata Tech Park
  and Electronic City. They are given as **addresses only**. Each hub's position comes from the
  response's `places_info`, never from hand-entered coordinates (ADR 0022).
- **One search per locality and hub**: from `AreaIntel.center` (`start_coords`), driving, km,
  leaving at a **pinned** departure (`COMMUTE_DEPART_AT`, Tuesday 09:00 local time). A
  "next weekday" departure would change the cache key every week, and recordings would stop
  replaying. A past date still returns typical traffic for that weekday and hour (S-04).
- **What is shown**: the first, recommended route's time (`duration`, a SerpApi field, as
  `Sourced[int]` with the search id and the Google Maps URL), Google's `typical_duration_range`
  (parsed to minutes when possible, otherwise shown as quoted), distance and `via`. Nothing is
  estimated in code.
- **Stored on the locality's area** as `AreaIntel.commutes` (by hub slug), so the run's frozen
  area and the property page carry it too.
- **Filled in on any run that lacks it, like rent levels**: no `AREA_SCHEMA_VERSION` bump, so
  areas cached before this change gain commutes without re-spending their six searches. A
  failing hub is recorded as section `commute:<hub>` and shown. It does not expire the rest of
  the area, and it is retried on the next run. A hub with no route is recorded as `empty` and
  is not searched again until the area expires.
- **Display only**, like news (ADR 0020), competitors (ADR 0023) and developing-area signals
  (ADR 0025). Commutes do not reach the area score, the ranking or the `summarize_area` prompt,
  so ranks and recorded explanations do not change. A test checks that the shortlist and scores
  are identical with and without hubs. Using commutes in the area score would need a change to
  ADR 0016.

## Consequences

- A new locality costs 3 more searches (9 in total for area intelligence), which are then free
  for the area's TTL. A fresh 3-locality apartment run rises from 32 to 41 lookups (Trends
  included), one over `SERPAPI_RUN_BUDGET` (40), so its last Trends request is stopped. Bigger
  runs stop earlier, and a hub cut off by the cap shows as "could not be loaded" and is filled
  in on the next run. Searches already made are served from the cache, so the retry costs only
  what was missing.
- Both demos are recorded: Whitefield to Manyata takes 1 hr 10 min at 9 AM (typically 55 min to
  1 hr 50 min). Koramangala to Electronic City takes 35 min.
- These are Google's usual-traffic times for one weekday hour, measured from the locality
  centre, not from each property. The UI says so.
- The hubs are not drawn on the map yet.
