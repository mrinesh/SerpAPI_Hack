# S-01 · Data coverage spike (Bengaluru)

- **Status:** Done (2026-10-04); design decisions recorded at the end
- **Searches spent:** 24 of the ~25 approved (1 smoke test on Oct 3, 23 recorded on Oct 4).
  Ledger: 23 live. SerpApi Account API after the spike: 227 left this month.
- **Fixtures:** 23 responses in `backend/fixtures/serpapi/` (1.3 MB), replayable for free
- **Analysis:** `uv run python scripts/s01_analyze.py` (reads fixtures only)

Goal: find out what SerpApi actually returns for Bengaluru property searches before the discovery
and cleaning design is locked.

## Setup
- [x] Canonical `location` from the Locations API: `Bengaluru,Karnataka,India` (target_type City; matches our default)
- [x] Mode: `SERPAPI_MODE=record`, all searches through the gateway (`app/cli.py`)
- Two searches timed out at the 30 s default and were not charged; retried with
  `SERPAPI_TIMEOUT_S=90`. OR = `site:99acres.com OR site:magicbricks.com OR site:nobroker.in`.

## Queries run

| # | Engine | Query (Google ones add `location`, `google.co.in`, `gl=in`, `hl=en`) | Portal results |
|---|---|---|---|
| 0 | google | `2 BHK flat for sale Whitefield Bangalore` (Oct 3 smoke test, not recorded) | 0/9 |
| 1 | google | `flat for sale in Whitefield Bangalore site:99acres.com` | 10/10 |
| 2 | google | same, `site:magicbricks.com` | 6/10 (only 1 MagicBricks) |
| 3 | google | same, `site:nobroker.in` | 0/10 (generic Bengaluru pages) |
| 4 | google | same + OR | 5/10 |
| 5 | google | `flat for sale in Whitefield Bangalore under 80 lakh` + OR | 10/10 |
| 6 | google | #4, `start=10` | 0/10 (clothing sales) |
| 7 | google | `independent house for sale in JP Nagar Bangalore under 2 crore` + OR | 3/10 |
| 8 | google | `builder floor for sale in Jayanagar Bangalore under 2 crore` + OR | 10/10 |
| 9 | google | `plot for sale in Yelahanka Bangalore under 1 crore` + OR | 0/10 (MATLAB "plot" pages) |
| 10 | google | `flat for sale in Electronic City Bangalore under 60 lakh` + OR | 9/10 |
| 11 | google | `2 BHK flat for sale in Hebbal Bangalore under 1 crore` + OR | 0/10 (generic Bengaluru pages) |
| 12 | google | `office space for sale in Koramangala Bangalore under 3 crore` + OR | 10/10 |
| 13 | google | `shop for sale in Indiranagar Bangalore under 2 crore` + OR | 6/10 |
| 14 | google | `warehouse for sale in KR Puram Bangalore` + OR | 10/10 (some for rent) |
| 15 | google | `commercial land for sale in Whitefield Bangalore` + OR | 8/10 |
| 16 | google_maps | `flats for sale Whitefield Bangalore` | 20 places |
| 17 | google_maps | `commercial property for sale Koramangala Bangalore` | 20 places |
| 18 | google_maps | `office space for sale Indiranagar Bangalore` | 20 places |
| 19 | google_local | `flats for sale in Whitefield Bangalore` | 20 places |
| 20 | google_local | `shop for sale in Indiranagar Bangalore` | 20 places |
| 21 | google_local | `real estate Whitefield Bangalore` | 20 places |
| 22 | google | `flat for sale in Hebbal Bangalore under 1 crore` + OR (#11 without "2 BHK") | 10/10 |
| 23 | google | `residential plot for sale in Yelahanka Bangalore under 1 crore` + OR (#9 reworded) | 10/10 |

## Findings per portal (87 portal results from Google)

| Portal | Results | Single listings | Project pages | Search / category pages | URL pattern |
|---|---|---|---|---|---|
| 99acres | 51 | 0 | 0 | 51 | ends `-ffid` (1 `-cffid`), optional `-page-N` |
| MagicBricks | 17 | 0 | 0 | 17 | ends `-pppfs` (for sale) or `-pppfr` (for rent), optional `/page-N` |
| NoBroker | 19 | 0 | 2 (`-prjtl`) | 17 | "...-for-sale-near-<landmark>_<locality>_bangalore", "...-below-N-lakhs-in-<locality>" |

**No result is a single listing.** Google returns the portals' search pages. Their snippets
still quote real entries, e.g. 99acres "SOWPARNIKA COLUMNS · ₹60 Lac. ₹8,185 /sqft", NoBroker
"4 BHK Flat For Sale In Whitefield. ₹1.70 Cr. ₹7,234/sq.ft.", MagicBricks "3 BHK Flat for Sale
in Whitefield Main Road … Prestige Park Grove. Carpet Area. 928 sqft. Status. Ready to Move."
Snippets are truncated ("…"); a working query yields about 4–10 prices.

## Field availability (share of portal results whose title + snippet contains it)

| Portal | Price | ₹ / sq ft | Size | BHK | Status | `rich_snippet` |
|---|---|---|---|---|---|---|
| 99acres | 62% | 49% | 56% | 43% | 52% | 0% |
| MagicBricks | 35% | 5% | 64% | 58% | 47% | 0% |
| NoBroker | 68% | 21% | 5% | 31% | 5% | 0% |

Posted dates did not appear. Locality appears in nearly every title.

## Query behaviour
- The three-portal OR filter works, but Google sometimes ignores the query and returns generic
  pages (4 of 15 Google queries). Seen with: an ambiguous word ("plot"), "2 BHK" in the query, a
  single `site:nobroker.in`, and page 2. Rewording fixed both retested cases (#22, #23).
- A budget phrase ("under 80 lakh", "under 1 crore") gave the cleanest results; page 2 was junk.
- Some for-rent pages appear despite "for sale" (MagicBricks `-pppfr`, NoBroker/99acres "for Rent"
  titles), so they must be filtered.

## Google Maps and Google Local

| Query | Useful types (of 20) | Verdict |
|---|---|---|
| Maps `flats for sale Whitefield` | Apartment complex 8, Apartment building 7, Condominium complex 2, Gated community 1 | Named residential projects with GPS, rating, reviews |
| Local `flats for sale in Whitefield` | Apartment complex 7, Apartment building 7, Condominium complex 4 | Same as Maps (largely the same places) |
| Maps `commercial property for sale Koramangala` | Real estate agencies / consultants | Not property supply |
| Maps `office space for sale Indiranagar` | Office rental agencies 10, Coworking 7 | Not for-sale property |
| Local `shop for sale in Indiranagar` | Clothing and grocery stores | Not relevant |
| Local `real estate Whitefield` | Agencies and agents | Not property supply |

All 120 places had GPS coordinates.

## Cost (S-03)
- 1 search per (locality × property type) query; page 2 adds nothing → 1 page.
- Profile with L localities and T property types: L × T searches on a fresh run, 0 within the
  cache TTL. Optional Maps project lookup: +1 per locality.

## Decisions
Pending the F-02 checkpoint with the product owner; recorded here once made.
