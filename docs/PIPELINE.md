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

> Status: plan, fetch and clean (F-02), verification (F-03, with F-12 price flags) and rank
> (F-04) are built, and enrich has area intelligence (F-05) and investment metrics (F-09). Both demo profiles replay end to end with no keys, from committed
> SerpApi and DeepSeek recordings. Discovery comes from S-01
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
- `price_levels` (`enrichment/price_level.py`, F-05 price level): before checking, one Google
  search per locality and property type ("flat price per sq ft in Whitefield Bangalore"); DeepSeek
  lite picks a quoted sale rate and its span, code validates it and takes a range's midpoint.
  Falls back to the median of ≥ 3 rates quoted in the run; otherwise no benchmark.
- `flag_listing` (`quality.py`, F-12): `too_good_to_be_true` (high) when the rate is under 40% of
  the benchmark, which catches rents quoted as sale prices; `missing_price` / `missing_size` (low).
  A high flag caps the verdict at weak and adds its reason to mismatches. Flags are applied in
  code, never sent to the verify prompt. No stale flag: search results carry no posted dates.
  See [ADR 0014](decisions/0014-area-relative-price-flags.md).

Rejected listings stay in the run with rank `null` so the UI can show what was filtered and why.

Extraction cannot replace any non-null field, including query-derived fields. New fields require
an exact span in the candidate's evidence, matching currency/units or enum words, and retain the
original sources. No evidence means no extraction call; Maps projects are still verified.
Budget, segment, type, locality and requested size violations override the model to reject.
Missing core facts and range/starting prices cap confidence and prevent a strong verdict.
ROI is explicitly unverified until F-09. See [ADR 0013](decisions/0013-grounded-verification.md).

At most `VERIFY_MAX_CANDIDATES` (default 16, about 2 DeepSeek calls each) are checked per run,
in discovery order, which is deterministic. The rest stay visible as "Not AI-checked" and are
counted as `unchecked`. The residential demo has 28 candidates; recordings cover the first 16.

Each completed check commits independently; progress counts checked and rejected candidates.
If a provider fails, the run fails with a clear error, while discovery and earlier checks remain
readable. `GET /api/runs/{id}/listings` returns run snapshots; `/verifications` returns completed
checks including rejects. The run UI refreshes these as verification advances. Enrichment and
composite ranking are separate future stages; relevance scores are not investment returns.

The LLM wrapper caches validated responses in `llm_cache`. Its key includes task, model, tier,
schema and prompt; record mode writes fixtures even on a DB cache hit. Replay reads only those
fixtures and fails on a miss. Prompts omit run timestamps and profile ID/name to reuse identical
criteria and evidence across repeat runs.

## 5 · Enrich (`enrichment/`, `metrics.py`, F-05, F-06, F-09)

**Area intelligence** (`enrichment/area.py`, F-05, [ADR 0016](decisions/0016-area-intelligence-and-score.md)):
once per locality of the rankable candidates, cached in `area_intel` for `AREA_INTEL_TTL_HOURS`:

| Signal | Engine | Query shape | Status |
|---|---|---|---|
| Locality centre | google_maps | `"{locality}, Bengaluru"`, rejected outside the city box | Built |
| Amenities | google_maps | `"metro station"`, `"school"`, `"hospital"` near the centre, zoom 14 | Built |
| Price growth, past 12 months | google | `"{locality} Bangalore property price trend year on year"` → `extract_price_growth` | Built |
| Price level per type | google | from the verify stage (`price_level.py`, ADR 0014), merged in | Built |
| Area + infrastructure summary | LLM lite | `summarize_area`, number-checked, code fallback | Built |
| News and infrastructure | google_news | `"{locality} Bengaluru"` → `classify_news` | Deferred |
| Rental demand (P1) | google_trends | `"flats for rent {locality}"`, up to 5 localities per call | Deferred |

Amenities are kept by Maps place type, with distances computed in code. The rank stage turns them
into the `area` score (metro, schools and hospitals within 3 km), measured from the listing's
coordinates when it has them, else the centre. Growth is stored for F-09, not scored here.
A provider error never fails a run, but it is never silent: each section records `ok`, `empty`
or `failed` with the error in `warnings`, a failed section makes the area expire at once so the
next run retries, and a cached area is reused only when it matches the current schema version
and provider modes ([ADR 0019](decisions/0019-visible-failures-validated-cache-withheld-metrics.md)).

**Competitors** (commercial only): google_maps `"{business_type}"` near the property →
density, ratings, review volume, saturation. P1: google_maps_reviews for the top competitors →
`competitor_gaps` prompt.

**Rent level** (`enrichment/rent_level.py`, F-09): one Google search per locality and type
("flat rent per sq ft in Whitefield Bangalore"); `extract_rent` (LLM lite) lists quoted rent
and size pairs; code checks each against its snippet and takes the median rent ÷ size of at
least 3 ([ADR 0017](decisions/0017-investment-metrics-and-roi-score.md)). Cached in the area.

**Metrics** (`metrics.py`, F-09): pure functions, no I/O:

| Metric | Formula |
|---|---|
| Price per sq ft | price / size |
| vs area average | (price per sq ft / locality average − 1) × 100 |
| Rental yield | area rent per sq ft per month × 12 / price per sq ft × 100, before any costs; withheld for a price flagged too good to be true or a starting / range price (ADR 0019) |
| Price growth | investor's override if set, else the locality's past-12-month change in price per sq ft |
| Total return | rental yield + price growth |
| Meets target | the goal's measure ≥ `target_roi_pct` (rental income → yield, appreciation → growth, balanced → total) |

No net yield or cap rate: both need cost assumptions we would have to source
([ADR 0010](decisions/0010-roi-definition.md)). Missing inputs give a missing metric, never zero.
The profile wizard suggests a target from the same sources before any run: the area's typical
yield, multi-year average growth, or both, adjusted for risk appetite
([ADR 0018](decisions/0018-suggested-target-roi.md)). The rank stage turns the goal's measure into the `roi` score: measure ÷ (1.5 × target) × 100,
capped at 100. Missing the target lowers the score; it never filters a candidate.

## 6 · Rank (`ranking.py`, F-04)

**In:** verified, enriched listings · **Out:** `list[Recommendation]`

Composite score computed in code, with weights set by `goal` and `risk_appetite`
([ADR 0015](decisions/0015-composite-ranking.md)): relevance (F-03 match score), value (price
per sq ft against the locality level), evidence (confidence and completeness), ROI vs target
(F-09, not available yet) and area signals (F-05, not available yet), minus 25 points per
high-severity flag. Unavailable components are left out and the rest renormalised;
`score_breakdown` gives each component's points, or `null`. Rejected and unchecked candidates
are not ranked. Ties go to the lower price, then the id.

Every ranked candidate gets a reason written by code. The top 5 also get one from
`explain_recommendation` (LLM lite tier), which receives pre-formatted display figures. Code
checks every number in its reason, highlights and risks against those figures; a failing
reason falls back to the code reason. Scores are saved before any explanation call, so a
provider failure keeps the ranking.

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
