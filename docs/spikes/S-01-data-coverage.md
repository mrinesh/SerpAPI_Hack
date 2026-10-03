# S-01 · Data coverage spike (Bengaluru)

- **Status:** Not started
- **Owner:**
- **Searches spent:** 0 / budget ~30

Goal: find out what SerpApi actually returns for Bengaluru property searches before the
discovery and cleaning design is locked. Run in `record` mode so every response becomes a fixture.

## Setup
- [ ] Canonical `location` from the Locations API: `________________`
- [ ] Mode: `SERPAPI_MODE=record`

## Queries run

| # | Engine | Query / params | Results | Fixture key |
|---|---|---|---|---|
| 1 | google | | | |

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
