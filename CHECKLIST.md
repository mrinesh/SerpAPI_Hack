# Project Checklist

Single source of truth for what is built, in progress and pending. Update it in the same commit
as the work (see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#definition-of-done)).

**Deadline:** Sat Oct 10, 2026, 23:59 IST · **Track:** Commerce & Market Intelligence ·
**Demo market:** Bengaluru

**Status legend:** ⬜ todo · 🟨 in progress · 🧱 scaffolded (interfaces and stubs exist, logic not
built) · ✅ done · ⏸️ deferred

**Priority:** **P0** must ship for the demo · **P1** should ship · **P2** stretch / post-hackathon

Code that is not built yet raises `NotImplementedYet("<ID>", ...)`, and the API returns
`501 {"error": {"code": "not_implemented", "details": {"feature_id": "<ID>"}}}`. Searching the
code for an ID finds every stub that belongs to it.

---

## Summary

| ID | Item | Priority | Status | Owner |
|---|---|---|---|---|
| **Spikes** | | | | |
| S-01 | Data coverage spike (Bengaluru, real queries) | P0 | ✅ | |
| S-02 | LLM extraction accuracy check | P0 | ✅ | |
| S-03 | Search cost model per run | P0 | ✅ | |
| S-04 | Commute directions: traffic-aware 9 AM times? | P1 | ✅ | |
| **Infrastructure** | | | | |
| I-01 | Repo scaffold, tooling, docs skeleton | P0 | ✅ | |
| I-02 | SerpApi gateway: params, cache, TTL | P0 | ✅ | |
| I-03 | SerpApi record / replay fixtures | P0 | ✅ | |
| I-04 | Search budget ledger and caps | P0 | ✅ | |
| I-05 | Budget endpoint via SerpApi Account API | P1 | ✅ | |
| I-06 | DeepSeek provider with structured output | P0 | ✅ | |
| I-07 | LLM record / replay cache | P0 | ✅ | |
| I-08 | Database schema and session | P0 | ✅ | |
| I-09 | Pipeline orchestrator, background runs, stage events | P0 | ✅ | |
| I-10 | Frontend shell, routing, API client, generated types | P0 | ✅ | |
| I-11 | Background scheduler | P1 | 🧱 | |
| I-12 | Bengaluru locality data and geocoding | P0 | ✅ | |
| I-13 | Recorded demo fixtures for judges | P0 | ✅ | |
| I-14 | CI: lint, typecheck, tests on push | P1 | ✅ | |
| **Features (F-01 to F-08 match the product brief's numbering)** | | | | |
| F-01 | Investor profile | P0 | ✅ | |
| F-02 | Property discovery | P0 | ✅ | |
| F-03 | AI relevance verification | P0 | ✅ | |
| F-04 | Ranked recommendations with reasons | P0 | ✅ | |
| F-05 | Area intelligence | P0 | ✅ | |
| F-06 | Competitor analysis (commercial) | P0 | ✅ | |
| F-07 | Property detail page | P0 | ✅ | |
| F-08 | Saved properties and side-by-side compare | P1 | 🧱 | |
| F-09 | Investment metrics | P0 | ✅ | |
| F-10 | Alerts (new match, price drop) | P1 | 🧱 | |
| F-11 | Source citations and confidence | P0 | ✅ | |
| F-12 | Listing quality flags | P1 | ✅ | |
| F-19 | Results map view | P0 | ✅ | |
| F-20 | Live pipeline progress view | P0 | ✅ | |
| F-22 | Parser fixes from S-02 | P1 | ⬜ | |
| F-23 | Commute to job hubs (google_maps_directions) | P1 | ✅ | |
| **Later (P2)** | | | | |
| F-13 | Risk scoring (flood, legal, oversupply) | P2 | ⏸️ | |
| F-14 | Neighbourhood trend forecasting | P2 | ⏸️ | |
| F-15 | PDF investment report export | P2 | ⏸️ | |
| F-16 | Portfolio tracker | P2 | ⏸️ | |
| F-17 | Scenario calculator (loan, EMI, exit) | P2 | ⏸️ | |
| F-18 | Natural-language search → profile | P2 | ⏸️ | |
| F-21 | Auth and multi-user | P2 | ⏸️ | |
| **Docs and submission** | | | | |
| D-01 | Docs kept current (see Docs section) | P0 | ✅ | |
| SUB | Hackathon submission | P0 | ⬜ | |

---

## Timeline

| Day | Date | Goal | Items |
|---|---|---|---|
| 0 | Sat Oct 3 | Framework; start the coverage spike | I-01 ✅, S-01 |
| 1 | Sun Oct 4 | SerpApi and LLM plumbing; spike conclusions | S-01, S-02, S-03, I-02–I-04, I-06, I-07, F-01 |
| 2 | Mon Oct 5 | Discovery and verification end to end | F-02, F-03, I-08, I-09, I-12 |
| 3 | Tue Oct 6 | Enrichment and ranking: full pipeline in replay | F-05, F-09, F-04 |
| 4 | Wed Oct 7 | UI core and commercial path | I-10, F-01 UI, F-20, F-19, F-07, F-06 |
| 5 | Thu Oct 8 | Trust and comparison; **first submit (locks timestamp)** | F-11, F-12, F-08, SUB draft |
| 6 | Fri Oct 9 | Alerts, demo fixtures, fresh-clone test | F-10, I-13, I-14, D-01 |
| 7 | Sat Oct 10 | Demo video, final submission, buffer | SUB |

---

## Spikes

### S-01 Data coverage spike · P0 · ✅
Answers the brief's biggest risk: what SerpApi actually returns for Bengaluru property searches.
Findings in [docs/spikes/S-01-data-coverage.md](docs/spikes/S-01-data-coverage.md); decisions in
[ADR 0011](docs/decisions/0011-discovery-from-search-snippets.md). 24 searches of the 25 approved.
- [x] Confirm `location` canonical name with the free Locations API: `Bengaluru,Karnataka,India`
- [x] 15 Google queries across 99acres / MagicBricks / NoBroker (Housing.com dropped by the product
      owner), residential and commercial, recorded as fixtures
- [x] 3 Google Maps and 3 Google Local queries
- [x] Per portal: single listings 0 of 87; all search pages (+2 NoBroker project pages)
- [x] Per field: price, ₹/sq ft, size, BHK, status coverage measured; no posted dates, no rich_snippet
- [x] Query templates decided with the product owner and implemented in `query_planner.py`
- [x] google_news and "property rates" queries built in F-05; google_trends built for
      developing-area signals (ADR 0025)

### S-02 LLM extraction accuracy · P0 · ✅
Findings: [docs/spikes/S-02-extraction-accuracy.md](docs/spikes/S-02-extraction-accuracy.md).
- [x] Hand-label 20 S-01 hits: `fixtures/spikes/s02_labels.json` (19 listings, 1 filter phrase;
      labelled by Claude Code from the snippet text, **to be reviewed by the product owner**)
- [x] Regex vs `extract_listing` alone vs shipped, per field (`scripts/s02_accuracy.py`, 31
      DeepSeek lite calls recorded, replayed by `test_s02_replay.py`): regex 19/19 on price,
      rate and BHK, 18/19 on size and status; the LLM alone is never wrong but misses what needs
      arithmetic (15/19 prices, 14/19 sizes) and gets status 19/19
- [x] Decision: regex first for every field, the LLM stays a gap filler; three parser fixes
      found, tracked as F-22

### S-03 Search cost model · P0 · ✅
- [x] Fresh run: L × T Google + L Maps (flats only); repeat run within the TTL: 0
- [x] Commercial run: L × T Google, no Maps
- [x] `SERPAPI_RUN_BUDGET` 40 covers the largest profile (25); model in docs/SERPAPI_USAGE.md
      (raised to 45 on 2026-10-08 so a fresh 3-locality run, 41 with F-23's commutes, fits)

### S-04 Commute directions · P1 · ✅
- [x] 4 searches, Whitefield → Manyata at four departures: times are traffic-aware (40 min vs
      1 hr 10 min); `depart_at` is read as local wall-clock time; a past date still works
      ([S-04](docs/spikes/S-04-commute-directions.md))

---

## Infrastructure

### I-01 Repo scaffold · P0 · ✅
- [x] Backend package layout, FastAPI app factory, settings, error contract
- [x] Domain schemas (`app/schemas`), DB models, stage and service stubs
- [x] Frontend shell (Vite, React, TypeScript, Tailwind, Router, TanStack Query, Leaflet)
- [x] Makefile, `.env.example`, docs skeleton, ADRs, this checklist
- [x] Tests: health, 501 contract, cache key, profile validation

### I-02 SerpApi gateway · P0 · ✅
`backend/app/integrations/serpapi/gateway.py`
- [x] `cache_key` (stable, ignores `api_key` and param order) + tests
- [x] Engine parameter builders in `engines.py`, checked against SerpApi docs (no `num`; Google Local added)
- [x] `search()`: DB cache lookup with TTL → live call via `serpapi.Client` → write cache
- [x] Map SerpApi errors (`SerpApiError`, timeouts, non-Success status) to `AppError`s
- [x] Tests with a fake client (13 cases)
- [x] Developer CLI `app/cli.py` for one-off searches through the gateway

### I-03 SerpApi record / replay · P0 · ✅
- [x] Record mode writes `fixtures/serpapi/<engine>/<key>.json` (with `api_key` stripped), also from cache
- [x] Replay mode reads fixtures only and raises `ReplayMiss` on a miss
- [x] `make record` and the CLI documented in docs/DEVELOPMENT.md
- [x] `make fixtures`: unused LLM recordings fail the check, `--prune` removes them; SerpApi
      recordings are reported only

### I-04 Search budget · P0 · ✅
- [x] Write every lookup to `search_ledger` (live or cached)
- [x] Enforce `SERPAPI_RUN_BUDGET` per run and `SERPAPI_MONTHLY_BUDGET` per calendar month
- [x] Surface searches used and cache hits on the run (`PipelineRun.searches_used`)

### I-05 Budget endpoint · P1 · ✅
- [x] `GET /api/meta/budget`: ledger totals + `Client.account()` searches left (skipped in replay)
- [x] Budget chip in the app header

### I-06 DeepSeek provider · P0 · ✅
DeepSeek V4 Pro replaced Gemini before any Gemini code existed (ADR 0012).
- [x] `generate_structured`: JSON mode, Pydantic schema in the system prompt; validate; retry once
- [x] `generate_text`
- [x] Model tiers: `DEEPSEEK_MODEL` with thinking for reasoning, `DEEPSEEK_MODEL_LITE` without
  thinking for extraction (both `deepseek-v4-pro`)
- [x] `python -m app.cli llm "<prompt>"` for a live connectivity check

### I-07 LLM record / replay · P0 · ✅
- [x] Cache in `llm_cache`, fixtures in `fixtures/llm/<task>/<key>.json`
- [x] Validated record/replay, model/tier/schema-aware keys, no network or DB cache in replay;
      tested with fake provider outputs
- [x] Replay mode runs the whole demo without a DeepSeek key (`test_demo_replay.py`)

### I-08 Database · P0 · ✅
- [x] Tables defined in `app/db/models.py`, created on startup
- [x] WAL mode, `busy_timeout`, foreign keys on (ADR 0009)
- [x] Persistence helpers as features needed them (`pipeline/persist.py`, services); F-08/F-10
      add theirs
- [x] docs/DATA_MODEL.md audited against `models.py` (2026-10-07): all 14 tables, keys and
      columns, with the frozen per-run tables in the diagram

### I-09 Pipeline orchestrator · P0 · ✅
- [x] `start_run`: create run row, launch `run_pipeline` in a background thread
- [x] Emit `StageEvent`s with counts per stage; persist partial results
- [x] Failure handling: failed stage marks run failed, earlier results stay viewable
- [x] Each later feature added its stage (verify F-03, enrich F-05/F-06/F-09, rank F-04)

### I-10 Frontend shell · P0 · ✅
- [x] Routes and placeholder pages for every screen
- [x] Typed API client with the shared error shape
- [x] `make types` generates `src/api/schema.d.ts` from OpenAPI (rerun after schema changes)
- [x] TanStack Query hooks for every endpoint a screen uses (health, budget, profile options,
      profiles, target suggestion, runs and their listings, checks, areas, competitors,
      recommendations, property detail). F-08/F-10 add theirs; `/areas/{key}` needs none

### I-11 Scheduler · P1 · 🧱
- [x] APScheduler wiring, off by default (`SCHEDULER_ENABLED`)
- [ ] Alert job wired to F-10

### I-12 Locality data and geocoding · P0 · ✅
- [x] `app/reference/bengaluru.json`: 15 localities verified on Wikipedia's neighbourhood list, with slugs
- [x] Geocode each locality centre via google_maps (F-05), kept with the area for its TTL and
      in replay fixtures; rejected outside the market's bounding box
- [x] Locality matching (observed aliases, joined initials, fuzzy for long names, landmarks
      ignored) used by cleaning (ADR 0024): locality evidence from the result's own words and a
      `location_mismatch` flag; both demos re-recorded (52 DeepSeek calls, 0 searches), 52
      superseded recordings pruned. Area news matching is unchanged (ADR 0020)

### I-13 Demo fixtures · P0 · ✅
- [x] Two demo profiles in `app/reference/demo_profiles.py`: apartment in Whitefield ≤ ₹80 L;
      office in Koramangala ≤ ₹3 Cr for IT services. `make demo` seeds them on startup
      (`SEED_DEMO_PROFILES`), so a fresh clone opens with runnable profiles
- [x] Both demo runs recorded end to end (searches and DeepSeek calls) and replayed in
      `test_demo_replay.py`
- [x] `make setup && make demo` on a fresh clone with no `.env`: both profiles seeded, both runs
      succeed with 0 searches (2026-10-07)

### I-14 CI · P1 · ✅
- [x] GitHub Actions (`.github/workflows/ci.yml`): `make lint` (ruff, eslint, tsc), `make test`,
      `vite build` and `make fixtures`, in replay mode with no secrets. First run on the `ci`
      branch passed in 1 min 16 s (2026-10-07); badge in the README

---

## Features

### F-01 Investor profile · P0 · ✅
- [x] Fields decided with the product owner (2026-10-03): name, segment, property types, size,
      business type (commercial), 1–5 localities, must-haves, budget, goal, target ROI,
      growth override, risk appetite. No bedrooms.
- [x] Schema with field-level validation (`InvestorProfileIn`); `roi_measure` from the goal (ADR 0010)
- [x] Property types grouped from the portals' categories (NoBroker, 99acres)
- [x] Profile CRUD + `DELETE`, checks against reference data, `GET /api/meta/profile-options`
- [x] One 422 shape for schema and reference-data errors
- [x] Profiles page and 3-step wizard (What → Where → Money), lakh/crore budget input
- [x] Suggested target ROI on the Money step from sourced area yield / multi-year growth,
      adjusted for risk; never overwrites the investor's value (ADR 0018)
- [x] Tests: 25 schema, 8 API, 15 frontend (money + form logic); checked in Chrome

### F-02 Property discovery · P0 · ✅
Design from S-01 and the product owner's checkpoint ([ADR 0011](docs/decisions/0011-discovery-from-search-snippets.md)).
- [x] `plan_queries`: one Google search per locality × type with the tested wording, retry without
      budget, Google Maps projects for flats
- [x] `fetch_hits`: portal pages (no rentals) and Maps housing places → `RawSearchHit`
- [x] Snippet-entry parsing: prices (Lac / Cr, ranges, "from"), ₹/sq ft, size (sq ft / sq m / sq yd),
      BHK, status, type words, names; filters, statistics and EMIs skipped
- [x] Candidates: priced snippet entries + Maps projects, matched by name; page-title fallbacks noted
- [x] De-duplication and stable candidate ids across runs
- [x] `listings` columns `price_inr`, `size_sqft`, `price_per_sqft` and `listing_observations`
- [x] Runs from the app: "Find properties" → run page with candidates
- [x] Tests built from verbatim fixture text (34 parser/planner, 6 end-to-end run cases)

### F-03 AI relevance verification · P0 · ✅
- [x] `extract_listing` prompt + `extract` (fills regex gaps only, checks evidence and units)
- [x] `verify_listing` prompt + `verify` → `Verification`; hard constraints enforced in code
- [x] Pipeline stage with incremental progress/persistence; per-run listing snapshots
- [x] `GET /api/runs/{id}/verifications`; rejected listings retained with null rank
- [x] Run UI shows match score, confidence, matched/missing criteria and "Filtered out" reasons
- [x] Offline tests: evidence grounding, constraints, uncertainty, persistence, failures, replay
- [x] Live DeepSeek acceptance and committed demo recordings
      (`backend/scripts/record_verification.py`): residential first 16 of 28, commercial all 6
- [x] `VERIFY_MAX_CANDIDATES` (default 16) caps DeepSeek spend per run; rest shown unchecked

### F-04 Ranked recommendations · P0 · ✅
- [x] Composite score in code, weights by goal and risk appetite, `score_breakdown` (ADR 0015);
      ROI and area-signal components are `null` until F-09 / F-05 fill them
- [x] `explain_recommendation` prompt: reason, highlights, risks; top 5 per run, every number
      checked against display figures, code reason as fallback
- [x] "Recommended" tab on the run page: rank, score, reason, highlights, risks, breakdown
- [x] Recorded for both demos (9 lite calls); tests for weights, value curve, penalties,
      ties, number guard, failure handling and demo replay

### F-05 Area intelligence · P0 · ✅
- [x] `locality_key` + cache per locality with TTL (`area_intel`, 7 days)
- [x] Amenities from google_maps (metro, school, hospital) with distances (ADR 0016)
- [x] News from google_news, classified by topic and sentiment; display only (ADR 0020, after
      gscode007's branch, reusing their recordings)
- [x] Frozen per-run area evidence (`run_area_intel`)
- [x] Price level per sq ft from google search (`enrichment/price_level.py`, ADR 0014), shown
      per type in the area panel; past-12-month growth from its own search (`extract_price_growth`)
- [x] Area summary + infrastructure summary, number-checked, code fallback
- [x] Area score fills F-04's `area` component (amenity access only; growth reserved for F-09)
- [x] Area panel on the run page; access line on recommendation cards
- [x] Recorded for both demos (10 searches, 4 lite calls; 9 explanations re-recorded)
- [x] P1: search demand from google_trends (up to 5 localities per call) with weekly charts:
      developing-area signals, display only (ADR 0025, ported from gscode007's branch with their
      code, tests and recordings)

### F-06 Competitor analysis (commercial) · P0 · ✅
Per locality and business type, read by property type, display only
([ADR 0023](docs/decisions/0023-competitors-per-locality-read-by-type.md)).
- [x] Same-category places via google_maps at the locality centre (commercial candidates carry no
      GPS), kept within 2 km; cached per locality, centre, business and radius; frozen per run
- [x] Density, density level (10+ high, 4–9 medium), average rating, total reviews; competition
      for shops, business cluster for offices, warehouses and land
- [x] `GET /api/runs/{id}/competitors`; `PropertyDetail.competitors` and its sources
- [x] Competitor card beside the area card, map layer on the run and detail maps
- [x] Failed search shown and retried next run; never fails the run, never changes ranks
- [x] Recorded for the commercial demo (1 search); tests: 18 unit, 3 replay (report, ranks unchanged, profile delete), 1 detail, 4 frontend
- [ ] F-06b (P1): review-gap analysis via google_maps_reviews + `competitor_gaps` prompt

### F-07 Property detail page · P0 · ✅
Run-scoped, from stored results only ([ADR 0021](docs/decisions/0021-run-scoped-property-detail.md)).
- [x] `GET /api/properties/{id}?run_id=` assembling listing, verification, recommendation, metrics,
      the run's area, price history and sources; latest run when `run_id` is omitted
- [x] Detail page layout: header facts, relevance check, metrics, reasons, area card, sources;
      linked from every run card. Map with amenities from F-19; competitors card and layer from F-06
- [x] Tests: 9 API cases on both demos (ranked, rejected, unchecked, latest run, 404s), 3 source
      cases; checked in Chrome on the commercial demo

### F-08 Saved and compare · P1 · 🧱
- [ ] Save / unsave / list
- [ ] Compare 2–4 properties side by side, best value per row highlighted

### F-09 Investment metrics · P0 · ✅
- [x] Rent estimate (`extract_rent` from search results): median of ≥ 3 checked rent ÷ size
      pairs per locality and type (ADR 0017)
- [x] ROI definition settled: rental yield, price growth, total return; no net yield or cap rate (ADR 0010)
- [x] Price per sq ft vs area average, rental yield, price growth (override or locality), total return
- [x] `meets_target_roi` using the goal's measure; ROI score fills F-04's `roi` component
- [x] Exhaustive unit tests (pure functions)
- [x] Cards show yield before costs, growth, total and a target badge; area panel shows rents
- [x] Recorded for both demos (2 rent calls, 9 explanations re-recorded; no new searches)

### F-10 Alerts · P1 · 🧱
- [ ] Diff against `listings`: new matches and price drops
- [ ] `POST /api/alerts/check` for the demo, scheduler for real use
- [ ] Alerts page and unread badge

### F-11 Source citations and confidence · P0 · ✅
- [x] `Sourced[T]` on every investor-facing field (schemas)
- [x] `<SourcedValue>` UI component: value, confidence badge, method, note and source links
- [x] "Where this came from" panel on the detail page (`collect_sources`, ADR 0021)

### F-12 Listing quality flags · P1 · ✅
- [x] Too-good-to-be-true (price per sq ft under 40% of the sourced locality level, run-median
      fallback, no flat rate; ADR 0014); catches S-01's "₹3.6 Lac … ₹75 /sqft … 4,800 sqft"
- [x] Missing price/size (duplicates are already merged in cleaning). No stale flag: no posted dates
- [x] Flag chips on run cards
- [x] Flag chips on the detail page (F-07)

### F-19 Results map view · P0 · ✅
Positions only from SerpApi ([ADR 0022](docs/decisions/0022-map-positions-only-from-serpapi.md)).
- [x] Leaflet + OpenStreetMap tiles on the run page: ranked candidates numbered and coloured by
      score band, the rest by status; Maps projects (and entries matched to one) at their own GPS,
      the rest grouped in one dashed marker at the locality centre from F-05, never jittered
- [x] Overlays: filtered out (off by default) and metro / schools / hospitals (on when no
      candidate has its own position); legend lists only the colours on the map
- [x] Detail page map: the property, its area's amenities and, for commercial runs, competitors (F-06)
- [x] Tests: 8 layout cases (placement, ungeocoded centres, status order, draw order, amenity
      de-duplication, opening view, colours, legend); checked in headless Chrome on both demos

### F-22 Parser fixes from S-02 · P1 · ⬜
Each has its S-02 entry as the test case ([S-02](docs/spikes/S-02-extraction-accuracy.md)).
- [ ] Take a stated size range ("ranging from 1415.0 sq. ft. to 1470.0 sq. ft.") before computing
      size from price ÷ rate
- [ ] Do not read sale status from page filter text ("Buy Ready to move, Resale, …")
- [ ] Skip "<price> Flats for" page-description phrases as entries

### F-23 Commute to job hubs · P1 · ✅
- [x] `google_maps_directions` builder and CLI; `COMMUTE_DEPART_AT` pinned to Tuesday 09:00
      local time (ADR 0026)
- [x] Three hubs by address in `bengaluru.json` (ORR/Bellandur, Manyata, Electronic City);
      positions only from `places_info`
- [x] `AreaIntel.commutes`: Google's route time (`Sourced`), typical range, km, via; filled in on
      any run lacking it, `commute:<hub>` section on failure, no schema bump
- [x] Area card "Drive to job hubs, weekday 9 AM" on the run and property pages; enrich note
- [x] Display only: the shortlist and scores are identical with and without hubs (test)
- [x] Recorded for both demos (5 searches, plus S-04's Whitefield → Manyata); tests for the parser,
      ranges, departure reading, fill-in, failure and replay

### F-20 Live pipeline progress · P0 · ✅
- [x] Poll `GET /api/runs/{id}`; show each stage with counts, searches used, cache hits

---

## Docs (D-01)

Kept current as features land. ✅ means the doc exists and matches the code today.

- [x] README.md: overview, quickstart, layout
- [x] docs/PRODUCT.md, docs/ARCHITECTURE.md, docs/PIPELINE.md
- [x] docs/SERPAPI_USAGE.md (doubles as the submission's SerpApi explanation)
- [x] docs/DATA_MODEL.md, docs/API.md, docs/DEVELOPMENT.md
- [x] docs/decisions/ ADR 0001–0025
- [x] docs/spikes/S-01 filled with real findings
- [x] Screenshots in README (`docs/images/`, from the replay demo)
- [x] Final pass: API.md matches the routes in `openapi.json` exactly, each with its real status
      (2026-10-07)

---

## Submission (SUB)

From [HACKATHON_BRIEF.md](HACKATHON_BRIEF.md#submission-checklist); details in [docs/SUBMISSION.md](docs/SUBMISSION.md).

- [x] Choose a license and add `LICENSE` (MIT, "Realty Intel contributors"; confirm)
- [x] Secrets scan: no keys in any branch's history (2026-10-07)
- [ ] Public GitHub repo (private today; make public before submitting)
- [x] Fresh-clone test: `make setup && make demo` works with no `.env` (2026-10-07)
- [ ] **First submit by Thu Oct 8** (timestamp locks on first submit; edits allowed after)
- [ ] Demo video under 3 min, running locally, opens in incognito
- [x] Project description and SerpApi usage explanation drafted in docs/SUBMISSION.md
- [ ] Paste them into the form
- [ ] Disclosures: new project; AI tools used (Claude Code, DeepSeek); community source = BangPypers (confirm)
- [ ] Track: Commerce & Market Intelligence
- [ ] Teammates added (name + email), all of whom contributed
- [ ] Tick: rules, terms, links tested in incognito
