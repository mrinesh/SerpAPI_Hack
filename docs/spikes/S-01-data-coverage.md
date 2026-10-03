# S-01 · Data coverage spike (Bengaluru)

- **Status:** In progress (smoke test done 2026-10-03)
- **Owner:**
- **Searches spent:** 1 / budget ~30

Goal: find out what SerpApi actually returns for Bengaluru property searches before the
discovery and cleaning design is locked. Run in `record` mode so every response becomes a fixture.

## Setup
- [x] Canonical `location` from the Locations API: `Bengaluru,Karnataka,India` (target_type City; matches our default)
- [ ] Mode: `SERPAPI_MODE=record`

## Queries run

| # | Engine | Query / params | Results | Fixture key |
|---|---|---|---|---|
| 1 | google | `2 BHK flat for sale Whitefield Bangalore`, location Bengaluru, google.co.in, gl=in | 9 organic, 0 relevant | not recorded (pre-gateway smoke test, id `6ac1268f9d26cf0dc8004e0e`) |

## Early observations

- **Plain queries return junk.** Query 1 (no `site:` filter) returned zero portal listings: furniture
  rental, a DDA Delhi page, a builder blog, a Hyderabad auction notice, YouTube, MakeMyTrip,
  Instagram. Related searches were "2 BHK means" style. Site-filtered queries are required, not
  optional; test them next.
- The response also had `ai_overview` (only a `page_token`; fetching it is a separate request),
  `related_questions`, `related_searches` and `pagination`.

## Findings per portal

| Portal | Hits | Single listings | Projects | Aggregate pages | Notes |
|---|---|---|---|---|---|
| 99acres | | | | | |
| MagicBricks | | | | | |
| Housing.com | | | | | |
| NoBroker | | | | | |

## Field availability (share of single-listing hits)

| Field | In title | In snippet | In rich_snippet | Not found |
|---|---|---|---|---|
| Price | | | | |
| Size (sq ft) | | | | |
| BHK | | | | |
| Locality | | | | |
| Posted date | | | | |

## Enrichment engines

| Engine | Query | Useful? | Notes |
|---|---|---|---|
| google_maps | amenities near a locality | | |
| google_news | `<locality> Bengaluru` | | |
| google | `<locality> property rates per sq ft` | | |
| google_trends | rent interest, 3 localities | | |
| google_maps | competitors, commercial | | |

## Decisions
- Query templates:
- Fields we can rely on:
- Fields that need the LLM:
- Design changes required (update PIPELINE.md, SERPAPI_USAGE.md, ADRs):
