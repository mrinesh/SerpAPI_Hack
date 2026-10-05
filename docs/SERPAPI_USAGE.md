# SerpApi Usage

How the platform depends on SerpApi. This page doubles as the source for the hackathon
submission's "SerpApi usage explanation". Facts marked *(docs)* were checked against SerpApi's
documentation on 2026-10-04; *(S-01)* against our recorded searches
([spike S-01](spikes/S-01-data-coverage.md)).

## Why the product needs search data

There is no open, structured property database for Indian cities. The facts an investor needs
(asking prices, what is being built nearby, what the area costs, how busy the competition is)
are spread across listing portals, Maps, news and search trends. SerpApi is how the platform
reads all of them through one consistent API. Every candidate property is built from search
results fetched for that investor's criteria; without SerpApi there is no shortlist.

## Engines and their roles

| Engine | Used for | Status |
|---|---|---|
| `google` | Discovery: site-filtered searches of 99acres, MagicBricks and NoBroker. Google returns their search pages, whose snippets quote priced entries *(S-01)*. Also the locality price level per sq ft ("office space price per sq ft in Koramangala Bangalore"), the benchmark for price flags (ADR 0014) | Built (F-02, F-12) |
| `google_maps` | Discovery: named housing projects with GPS, rating and reviews for flat profiles *(S-01)*. Later: amenities and commercial competitors | Discovery built (F-02); rest planned (F-05, F-06) |
| `google_news` | Neighbourhood news and infrastructure announcements | Planned (F-05) |
| `google_trends` | Rental and buying search interest, up to 5 localities per call | Planned (F-05) |
| `google_maps_reviews` | Review text of top competitors, to find market gaps | Planned (F-06b) |
| `google_local` | Tested in S-01: the same projects as Maps for flats, irrelevant results for commercial | Not used |

Free SerpApi APIs we use:
- **Account API** (`Client.account()`): searches left; free and not counted *(docs)*. Shown in the
  app header (I-05).
- **Locations API** (`Client.locations()`): confirmed the canonical `location`
  `Bengaluru,Karnataka,India` *(S-01)*.
- **Search Archive API**: every candidate keeps the `search_metadata.id` of the search it came
  from, so the original response can be re-opened later.

All parameters are built in one file:
[`backend/app/integrations/serpapi/engines.py`](../backend/app/integrations/serpapi/engines.py).
Google Search is paginated with `start`; the docs list no `num` parameter *(docs)*.

## SDK

The official [`serpapi`](https://pypi.org/project/serpapi/) Python package (`serpapi.Client`).
Only the gateway, `backend/app/integrations/serpapi/gateway.py`, imports it.

## Staying inside the free tier (250 searches / month)

| Mechanism | Where | Effect |
|---|---|---|
| Record / replay | `backend/fixtures/serpapi/` | Tests, development and the judges' demo spend nothing |
| Database cache with TTL | gateway, `serp_cache` | Repeat queries cost nothing for `SERPAPI_CACHE_TTL_HOURS` (72) |
| Deterministic query planning | `query_planner.py` | The same profile hits the same cache keys every time |
| Per-run and monthly caps | gateway, `search_ledger` | A run stops spending at `SERPAPI_RUN_BUDGET` (40) |
| Page 1 only | `query_planner.py` | Page 2 returned no portal results in S-01 |
| One retry at most | `discovery.py` | A query with no portal results is retried once without the budget phrase |

SerpApi itself does not count cached searches; its cache lasts 1 hour *(docs)*. Our database cache
sits in front of that for longer reuse. Searches that time out were not charged in S-01; the
default timeout is 60 s because two searches exceeded 30 s.

### Cost model *(S-01)*

| Run | Searches |
|---|---|
| Fresh run, L localities × T property types | L × T Google, + L Google Maps if flats are wanted, + at most 1 retry per empty query, + up to L × T price-level Google searches (localities with candidates) |
| Example: 3 localities, apartments only | 3 Google + 3 Maps + 3 price level = 9 |
| Largest profile: 5 localities × 4 types, with flats | 20 Google + 5 Maps + 20 price level = 45; the per-run cap of 40 stops discovery-first runs before that, and price levels then fall back to run medians |
| Repeat run within the cache TTL | 0 |

## Data handling

- Fixtures store public search results only; `api_key` is stripped before anything is written.
- The platform links to the portals' pages and never fetches or scrapes them
  ([ADR 0002](decisions/0002-serpapi-as-the-only-listing-source.md)).
