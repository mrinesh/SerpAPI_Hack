# SerpApi Usage

How the platform depends on SerpApi. This page doubles as the source for the hackathon
submission's "SerpApi usage explanation".

## Why the product needs search data

There is no open, structured property database for Indian cities. The facts an investor needs
(live listings, what is being built nearby, what the area costs, how busy the competition is)
are spread across listing portals, Maps, news and search trends. SerpApi is how the platform
reads all of them through one consistent API. Every recommendation is built from search results
fetched for that investor's criteria; without SerpApi there is no shortlist, no area
intelligence and no competitor view.

## Engines and their roles

| Engine | Used for | Pipeline stage | Feature |
|---|---|---|---|
| `google` | Listing discovery with site-filtered portal queries (99acres, MagicBricks, Housing.com, NoBroker); locality price levels; rent figures | Fetch, Enrich | F-02, F-05, F-09 |
| `google_maps` | Geocoding localities; nearby amenities (metro, schools, hospitals); same-category competitors for commercial property | Enrich | F-05, F-06, I-12 |
| `google_news` | Neighbourhood news and infrastructure announcements | Enrich | F-05 |
| `google_trends` | Rental and buying search interest over time, comparing up to 5 localities in one call | Enrich | F-05 (P1) |
| `google_maps_reviews` | Review text of top competitors, to find gaps in the local market | Enrich | F-06b (P1) |

Free SerpApi APIs we also use:
- **Account API** (`Client.account()`): searches left this month, shown in the app header (I-05).
- **Locations API** (`Client.locations()`): canonical `location` value for Bengaluru (S-01).
- **Search Archive API** (`Client.search_archive()`): every sourced value stores the
  `search_metadata.id` it came from, so the original response can be re-opened later.

All parameters are built in one file:
[`backend/app/integrations/serpapi/engines.py`](../backend/app/integrations/serpapi/engines.py).

## SDK

The official [`serpapi`](https://pypi.org/project/serpapi/) Python package (`serpapi.Client`).
Only the gateway, `backend/app/integrations/serpapi/gateway.py`, imports it.

## Staying inside the free tier (250 searches / month)

| Mechanism | Where | Effect |
|---|---|---|
| Database cache with TTL | gateway, `serp_cache` | Repeat queries cost nothing for `SERPAPI_CACHE_TTL_HOURS` |
| Locality-keyed enrichment | `enrichment/area.py` | Area searches are paid once per locality, not once per property |
| Deterministic query planning | `query_planner.py` | The same profile hits the same cache keys every time |
| Per-run and monthly caps | gateway, `search_ledger` | A run stops spending at `SERPAPI_RUN_BUDGET` |
| Record / replay | `fixtures/serpapi/` | Development, tests and the judges' demo spend nothing |
| Trends batching | `engines.google_trends` | One call compares up to 5 localities |

SerpApi also does not charge for its own cached results (identical searches within about an
hour). Our cache sits in front of that for longer-lived reuse.

### Cost model *(estimate; confirmed in S-03)*

| Run | Searches |
|---|---|
| Fresh residential run, 3 localities | ~6 discovery + ~3 geocode + ~9 amenities + ~3 news + ~3 price level + 1 trends ≈ **25** |
| Repeat run, same localities within TTL | ≈ **6** (discovery only) |
| Commercial run adds | ~1 competitor search per property cluster + ~3 review fetches (P1) |

## Data handling

- Fixtures store public search results only; `api_key` is stripped before anything is written.
- The platform links out to listing portals and never scrapes them directly
  ([ADR 0002](decisions/0002-serpapi-as-the-only-listing-source.md)).
