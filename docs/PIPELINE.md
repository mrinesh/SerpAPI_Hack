# Pipeline

From investor criteria to a ranked, explained shortlist. Orchestrated by
`backend/app/pipeline/orchestrator.py` (CHECKLIST I-09); each stage is one module.

```mermaid
flowchart LR
    P[Profile] --> PLAN[1 · Plan<br/>query_planner]
    PLAN --> FETCH[2 · Fetch<br/>discovery]
    FETCH --> CLEAN[3 · Clean<br/>cleaning]
    CLEAN --> VERIFY[4 · Verify<br/>verification + quality]
    VERIFY --> ENRICH[5 · Enrich<br/>area · competitors · metrics]
    ENRICH --> RANK[6 · Rank<br/>ranking]
    RANK --> R[Recommendations]
```

Each stage emits a `StageEvent` (status, message, counts) that the UI polls, so the demo shows
the pipeline working live (F-20). A failing stage marks the run failed without discarding
earlier results.

> Status: plan, fetch and clean are built (F-02); verify, enrich and rank are reported as "not
> built yet" in every run. The discovery design comes from spike S-01
> ([findings](spikes/S-01-data-coverage.md), [ADR 0011](decisions/0011-discovery-from-search-snippets.md)).

## 1 · Plan (`query_planner.py`, F-02)

**In:** `InvestorProfile` · **Out:** `list[PlannedQuery]`

Deterministic, so the same profile always costs the same searches and hits the same cache keys.

| Search | When | Query (S-01 wording) |
|---|---|---|
| Google | one per locality × property type, page 1 only | `{type} for sale in {locality} Bangalore under {budget}` + `site:99acres.com OR site:magicbricks.com OR site:nobroker.in` |
| Google, retry | only if the first returned no portal page | the same without `under {budget}` |
| Google Maps | one per locality, only when Apartment / Flat is chosen | `flats for sale {locality} Bangalore` |

Type words: flat, independent house, builder floor, residential plot, office space, shop,
warehouse, commercial land ("plot" alone returned MATLAB pages; "2 BHK" in the query returned
generic pages). Budget: "under 80 lakh", "under 1.5 crore". Cost on a fresh run: L × T Google
searches plus up to L Maps searches; nothing within the cache TTL.

## 2 · Fetch (`discovery.py`, F-02)

**In:** planned queries · **Out:** `list[RawSearchHit]` and a `FetchReport`

Runs each query through the SerpApi gateway (replay, cache, budget). Keeps Google results only
from the three portals and not for-rent pages (MagicBricks `-pppfr`, "for Rent" titles); keeps Maps
places only of the housing types seen in S-01. Each hit keeps its SerpApi `search_id`. A query that
fails (e.g. not recorded in replay mode) is reported and skipped; the search budget stops the
stage early. The stage fails only if nothing at all came back.

## 3 · Clean (`cleaning.py`, `persist.py`, F-02)

**In:** raw hits · **Out:** candidate `Listing`s, saved with one observation per run

Google never returns single listings, only the portals' search pages, so candidates are:
- **Snippet entries:** each priced entry quoted in a page's snippet, linked to that page.
- **Projects:** Google Maps housing places, with GPS, rating and reviews.

Snippet parsing is regex over NFKC-normalised text (MagicBricks writes "₹ 1 Crore" in math-bold
characters):
1. Split the snippet into segments at `;`, `・` and `…`; split again at each price.
2. Prices: `₹60 Lac`, `1.70 Cr`, `96.48 Lacs`, `rs4.65 crore`; ranges keep the lower bound and
   "₹3.57 Cr+" is a starting price (both noted). Skipped: filters and statistics ("between",
   "average price of", "within", "under"…), and EMIs / per-month amounts.
3. Per entry: ₹/sq ft (only if no other ₹ amount sits between it and the price), size (sq ft;
   sq m × 10.7639; sq yd × 9), BHK or "n bedrooms", sale status, property-type words.
   Missing BHK and status fall back to the page title ("2 BHK Flats in …", "Ready to move
   Flats …"), noted as such. Price = rate × size, or size = price ÷ rate, when one is missing
   (marked computed).
4. Name: 99acres' capitalised project before the price, NoBroker's "In <project> For Sale In",
   an entry headline, or "<BHK> <type> in <locality>".
5. Merge duplicates (same identity, or same locality and price with near-identical names);
   give entries the GPS of a Maps project with the same name.

Confidence is fixed per method: text 0.8, computed 0.6, taken from the search 0.5, Maps field 0.9.
Candidate ids are stable hashes, so a repeat run updates the same rows and adds observations.

## 4 · Verify (`verification.py`, `quality.py`, F-03, F-12)

**In:** listings + profile · **Out:** `Verification` per listing

- `extract` (LLM lite tier, prompt `extract_listing`): fills only the fields regex missed; each
  value carries confidence and the exact text span it came from.
- `verify` (LLM reasoning tier, prompt `verify_listing`): 0–100 match score, verdict, matched criteria,
  mismatches, missing data.
- `flag_listing` (rules): too-good-to-be-true (also catches rents quoted as sale prices),
  missing data. No stale flag: search results carry no posted dates.

Rejected listings stay in the run with rank `null` so the UI can show what was filtered and why.

## 5 · Enrich (`enrichment/`, `metrics.py`, F-05, F-06, F-09)

**Area intelligence**: once per locality, cached `AREA_INTEL_TTL_HOURS`:

| Signal | Engine | Query shape *(S-01)* |
|---|---|---|
| Locality centre | google_maps | `"{locality}, Bengaluru"` |
| Amenities | google_maps | `"metro station"`, `"school"`, `"hospital"` near the centre |
| News and infrastructure | google_news | `"{locality} Bengaluru"` → classified by `classify_news` |
| Price level | google | `"{locality} Bangalore property rates per sq ft"` |
| Rental demand (P1) | google_trends | `"flats for rent {locality}"` for up to 5 localities in one call |

**Competitors** (commercial only): google_maps `"{business_type}"` near the property →
density, ratings, review volume, saturation. P1: google_maps_reviews for the top competitors →
`competitor_gaps` prompt.

**Metrics**: pure functions, no I/O:

| Metric | Formula |
|---|---|
| Price per sq ft | price / size |
| vs area average | (price per sq ft / locality average − 1) × 100 |
| Rental yield | monthly rent × 12 / price × 100, before any costs |
| Price growth | investor's override if set, else the locality's past-12-month change in price per sq ft |
| Total return | rental yield + price growth |
| Meets target | the goal's measure ≥ `target_roi_pct` (rental income → yield, appreciation → growth, balanced → total) |

No net yield or cap rate: both need cost assumptions we would have to source
([ADR 0010](decisions/0010-roi-definition.md)). Missing inputs give a missing metric, never zero.

## 6 · Rank (`ranking.py`, F-04)

**In:** verified, enriched listings · **Out:** `list[Recommendation]`

Composite score computed in code, with weights set by `goal` and `risk_appetite`:
match score, ROI vs target, price vs area average, area signals, and quality-flag penalties.
`score_breakdown` exposes each component. The LLM (`explain_recommendation`) writes only the
reason, highlights and risks, quoting numbers from the inputs.

## LLM calls per run

| Prompt | Model tier | Calls |
|---|---|---|
| `extract_listing` | lite | ≤ 1 per listing, only when regex left gaps |
| `verify_listing` | reasoning | 1 per listing |
| `classify_news` | lite | 1 per new locality |
| `summarize_area` | reasoning | 1 per new locality |
| `extract_rent` | lite | 1 per new locality and unit type |
| `competitor_gaps` | reasoning | 1 per commercial property (P1) |
| `explain_recommendation` | reasoning | 1 per top-N listing |
