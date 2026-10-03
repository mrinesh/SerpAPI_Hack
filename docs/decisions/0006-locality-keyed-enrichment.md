# 0006. Enrich per locality, not per property

- **Status:** Accepted
- **Date:** 2026-10-03

## Context
Area intelligence (amenities, news, price level, demand) costs about 6 searches. Per property,
a 10-property shortlist would cost 60 searches, a quarter of the monthly free tier, in one run.

## Decision
Area intelligence is computed once per locality, keyed `city/locality` (e.g.
`bengaluru/whitefield`), stored in `area_intel` with a TTL, and shared by every listing in that
locality. Property-specific distances are computed locally from the shared amenity coordinates.

## Consequences
- Enrichment cost scales with localities (usually 1–4), not listings.
- Locality matching must be good (aliases, fuzzy matching; I-12), or listings get the wrong area.
