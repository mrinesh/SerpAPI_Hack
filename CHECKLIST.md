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
| S-01 | Data coverage spike (Bengaluru, real queries) | P0 | 🟨 | |
| S-02 | Gemini extraction accuracy check | P0 | ⬜ | |
| S-03 | Search cost model per run | P0 | ⬜ | |
| **Infrastructure** | | | | |
| I-01 | Repo scaffold, tooling, docs skeleton | P0 | ✅ | |
| I-02 | SerpApi gateway: params, cache, TTL | P0 | 🧱 | |
| I-03 | SerpApi record / replay fixtures | P0 | 🧱 | |
| I-04 | Search budget ledger and caps | P0 | 🧱 | |
| I-05 | Budget endpoint via SerpApi Account API | P1 | 🧱 | |
| I-06 | Gemini provider with structured output | P0 | 🧱 | |
| I-07 | LLM record / replay cache | P0 | 🧱 | |
| I-08 | Database schema and session | P0 | 🧱 | |
| I-09 | Pipeline orchestrator, background runs, stage events | P0 | 🧱 | |
| I-10 | Frontend shell, routing, API client, generated types | P0 | 🧱 | |
| I-11 | Background scheduler | P1 | 🧱 | |
| I-12 | Bengaluru locality data and geocoding | P0 | 🧱 | |
| I-13 | Recorded demo fixtures for judges | P0 | ⬜ | |
| I-14 | CI: lint, typecheck, tests on push | P1 | ⬜ | |
| **Features (F-01 to F-08 match the product brief's numbering)** | | | | |
| F-01 | Investor profile | P0 | 🧱 | |
| F-02 | Property discovery | P0 | 🧱 | |
| F-03 | AI relevance verification | P0 | 🧱 | |
| F-04 | Ranked recommendations with reasons | P0 | 🧱 | |
| F-05 | Area intelligence | P0 | 🧱 | |
| F-06 | Competitor analysis (commercial) | P0 | 🧱 | |
| F-07 | Property detail page | P0 | 🧱 | |
| F-08 | Saved properties and side-by-side compare | P1 | 🧱 | |
| F-09 | Investment metrics | P0 | 🧱 | |
| F-10 | Alerts (new match, price drop) | P1 | 🧱 | |
| F-11 | Source citations and confidence | P0 | 🧱 | |
| F-12 | Listing quality flags | P1 | 🧱 | |
| F-19 | Results map view | P0 | ⬜ | |
| F-20 | Live pipeline progress view | P0 | ⬜ | |
| **Later (P2)** | | | | |
| F-13 | Risk scoring (flood, legal, oversupply) | P2 | ⏸️ | |
| F-14 | Neighbourhood trend forecasting | P2 | ⏸️ | |
| F-15 | PDF investment report export | P2 | ⏸️ | |
| F-16 | Portfolio tracker | P2 | ⏸️ | |
| F-17 | Scenario calculator (loan, EMI, exit) | P2 | ⏸️ | |
| F-18 | Natural-language search → profile | P2 | ⏸️ | |
| F-21 | Auth and multi-user | P2 | ⏸️ | |
| **Docs and submission** | | | | |
| D-01 | Docs kept current (see Docs section) | P0 | 🟨 | |
| SUB | Hackathon submission | P0 | ⬜ | |

---

## Timeline

| Day | Date | Goal | Items |
|---|---|---|---|
| 0 | Sat Oct 3 | Framework; start the coverage spike | I-01 ✅, S-01 |
| 1 | Sun Oct 4 | SerpApi and Gemini plumbing; spike conclusions | S-01, S-02, S-03, I-02–I-04, I-06, I-07, F-01 |
| 2 | Mon Oct 5 | Discovery and verification end to end | F-02, F-03, I-08, I-09, I-12 |
| 3 | Tue Oct 6 | Enrichment and ranking: full pipeline in replay | F-05, F-09, F-04 |
| 4 | Wed Oct 7 | UI core and commercial path | I-10, F-01 UI, F-20, F-19, F-07, F-06 |
| 5 | Thu Oct 8 | Trust and comparison; **first submit (locks timestamp)** | F-11, F-12, F-08, SUB draft |
| 6 | Fri Oct 9 | Alerts, demo fixtures, fresh-clone test | F-10, I-13, I-14, D-01 |
| 7 | Sat Oct 10 | Demo video, final submission, buffer | SUB |

---

## Spikes

### S-01 Data coverage spike · P0 · 🟨
Answers the brief's biggest risk: what SerpApi actually returns for Bengaluru property searches.
Record findings in [docs/spikes/S-01-data-coverage.md](docs/spikes/S-01-data-coverage.md).
- [x] Confirm `location` canonical name with the free Locations API: `Bengaluru,Karnataka,India`
- [ ] Run ~10 residential queries across 99acres / MagicBricks / Housing / NoBroker, record fixtures
- [ ] Run ~4 commercial queries (office / retail) and 2 Google Maps competitor queries
- [ ] For each portal: share of hits that are single listings vs aggregate pages
- [ ] For each field (price, size, BHK, locality, posted date): how often it is in title / snippet / rich_snippet
- [ ] Check what google_news, google_trends and the "property rates" query return for 2 localities
- [ ] Decide final query templates and update `query_planner.py` docstring and docs/SERPAPI_USAGE.md

### S-02 Gemini extraction accuracy · P0 · ⬜
- [ ] Hand-label 20 S-01 hits (kind, price, size, BHK, locality)
- [ ] Run regex parsers + `extract_listing` and record field-level accuracy in the spike doc
- [ ] Decide which fields need the LLM and which regex handles alone

### S-03 Search cost model · P0 · ⬜
- [ ] Count searches for a fresh residential run (3 localities) and a repeat run
- [ ] Count extra searches for a commercial run
- [ ] Set `SERPAPI_RUN_BUDGET` and document the model in docs/SERPAPI_USAGE.md

---

## Infrastructure

### I-01 Repo scaffold · P0 · ✅
- [x] Backend package layout, FastAPI app factory, settings, error contract
- [x] Domain schemas (`app/schemas`), DB models, stage and service stubs
- [x] Frontend shell (Vite, React, TypeScript, Tailwind, Router, TanStack Query, Leaflet)
- [x] Makefile, `.env.example`, docs skeleton, ADRs, this checklist
- [x] Tests: health, 501 contract, cache key, profile validation

### I-02 SerpApi gateway · P0 · 🧱
`backend/app/integrations/serpapi/gateway.py`
- [x] `cache_key` (stable, ignores `api_key` and param order) + tests
- [x] Engine parameter builders in `engines.py` (confirm in S-01)
- [ ] `search()`: DB cache lookup with TTL → live call via `serpapi.Client` → write cache
- [ ] Map SerpApi errors (`SerpApiError`, timeouts) to `AppError`s
- [ ] Tests with a fake client

### I-03 SerpApi record / replay · P0 · 🧱
- [ ] Record mode writes `fixtures/serpapi/<engine>/<key>.json` (with `api_key` stripped)
- [ ] Replay mode reads fixtures only and raises `ReplayMiss` on a miss
- [ ] `make record` target documented in docs/DEVELOPMENT.md

### I-04 Search budget · P0 · 🧱
- [ ] Write every lookup to `search_ledger` (live or cached)
- [ ] Enforce `SERPAPI_RUN_BUDGET` per run and `SERPAPI_MONTHLY_BUDGET` per calendar month
- [ ] Surface searches used and cache hits on the run (`PipelineRun.searches_used`)

### I-05 Budget endpoint · P1 · 🧱
- [ ] `GET /api/meta/budget`: ledger totals + `Client.account()` searches left
- [ ] Budget chip in the app header

### I-06 Gemini provider · P0 · 🧱
- [ ] `generate_structured` with `response_schema` = Pydantic model; validate; retry once
- [ ] `generate_text`
- [ ] Model tiers: `GEMINI_MODEL` for reasoning, `GEMINI_MODEL_LITE` for extraction

### I-07 LLM record / replay · P0 · 🧱
- [ ] Cache in `llm_cache`, fixtures in `fixtures/llm/<task>/<key>.json`
- [ ] Replay mode runs the whole demo without a Gemini key

### I-08 Database · P0 · 🧱
- [x] Tables defined in `app/db/models.py`, created on startup
- [ ] Repository helpers as each feature needs them
- [ ] docs/DATA_MODEL.md kept in sync

### I-09 Pipeline orchestrator · P0 · 🧱
- [ ] `start_run`: create run row, launch `run_pipeline` in a background thread
- [ ] Emit `StageEvent`s with counts per stage; persist partial results
- [ ] Failure handling: failed stage marks run failed, earlier results stay viewable

### I-10 Frontend shell · P0 · 🧱
- [x] Routes and placeholder pages for every screen
- [x] Typed API client with the shared error shape
- [x] `make types` generates `src/api/schema.d.ts` from OpenAPI (rerun after schema changes)
- [ ] TanStack Query hooks per endpoint

### I-11 Scheduler · P1 · 🧱
- [x] APScheduler wiring, off by default (`SCHEDULER_ENABLED`)
- [ ] Alert job wired to F-10

### I-12 Locality data and geocoding · P0 · 🧱
- [x] `app/reference/bengaluru.json` with localities and aliases
- [ ] Geocode each locality centre via google_maps once; cache permanently
- [ ] Locality matching (aliases, fuzzy) used by cleaning and area intel

### I-13 Demo fixtures · P0 · ⬜
- [ ] Record one residential and one commercial demo run end to end
- [ ] Verify `make demo` works on a fresh clone with no `.env`

### I-14 CI · P1 · ⬜
- [ ] GitHub Actions: `ruff`, `pytest`, `tsc`, `eslint`, `vite build`

---

## Features

### F-01 Investor profile · P0 · 🧱
- [x] Schema with validation (`InvestorProfileIn`)
- [ ] Profile CRUD service + routes
- [ ] Onboarding form (residential / commercial branches, budget in lakhs/crores)
- [ ] Two seeded demo profiles (residential yield, commercial cafe)

### F-02 Property discovery · P0 · 🧱
- [ ] `plan_queries` templates (from S-01)
- [ ] `fetch_hits`: organic and local results → `RawSearchHit`
- [ ] Parsers: price (L / Cr / per month), area (sq ft / sq m / sq yd), portal, canonical URL
- [ ] Result kind classification (listing / project / aggregate)
- [ ] De-duplication (canonical URL, then fuzzy title + price + locality)
- [ ] Unit tests for every parser example in `cleaning.py`

### F-03 AI relevance verification · P0 · 🧱
- [ ] `extract_listing` prompt + `extract` (fills regex gaps only)
- [ ] `verify_listing` prompt + `verify` → `Verification`
- [ ] Rejected listings kept with reasons and shown in a "filtered out" list

### F-04 Ranked recommendations · P0 · 🧱
- [ ] Composite score in code, weights by goal and risk appetite, `score_breakdown`
- [ ] `explain_recommendation` prompt: reason, highlights, risks
- [ ] Results page list with score, reason and key metrics

### F-05 Area intelligence · P0 · 🧱
- [ ] `locality_key` + cache per locality with TTL
- [ ] Amenities from google_maps (metro, school, hospital) with distances
- [ ] News from google_news, classified by topic and sentiment
- [ ] Price level per sq ft from google search
- [ ] Area summary + infrastructure summary with citations
- [ ] P1: rental demand from google_trends (compare localities in one call) + chart

### F-06 Competitor analysis (commercial) · P0 · 🧱
- [ ] Same-category places near the property via google_maps
- [ ] Density, average rating, total reviews, saturation level
- [ ] Competitor map layer and table
- [ ] F-06b (P1): review-gap analysis via google_maps_reviews + `competitor_gaps` prompt

### F-07 Property detail page · P0 · 🧱
- [ ] `GET /api/properties/{id}` assembling listing, verification, metrics, area, competitors
- [ ] Detail page layout: header facts, metrics, area panel, competitors panel, sources

### F-08 Saved and compare · P1 · 🧱
- [ ] Save / unsave / list
- [ ] Compare 2–4 properties side by side, best value per row highlighted

### F-09 Investment metrics · P0 · 🧱
- [ ] Rent estimate (`extract_rent` from search results)
- [ ] Price per sq ft vs area average, gross and net yield, cap rate (commercial)
- [ ] Assumptions documented with sources in docs/PIPELINE.md
- [ ] Exhaustive unit tests (pure functions)

### F-10 Alerts · P1 · 🧱
- [ ] Diff against `listings`: new matches and price drops
- [ ] `POST /api/alerts/check` for the demo, scheduler for real use
- [ ] Alerts page and unread badge

### F-11 Source citations and confidence · P0 · 🧱
- [x] `Sourced[T]` on every investor-facing field (schemas)
- [ ] `<SourcedValue>` UI component: value, confidence badge, source link popover
- [ ] "Where this came from" panel on the detail page

### F-12 Listing quality flags · P1 · 🧱
- [ ] Too-good-to-be-true (price per sq ft vs locality average)
- [ ] Stale, duplicate, not-a-listing, missing price/size
- [ ] Flag chips on cards and the detail page

### F-19 Results map view · P0 · ⬜
- [ ] Leaflet + OpenStreetMap tiles, markers coloured by score
- [ ] Amenity and competitor layers on the detail page

### F-20 Live pipeline progress · P0 · ⬜
- [ ] Poll `GET /api/runs/{id}`; show each stage with counts, searches used, cache hits

---

## Docs (D-01)

Kept current as features land. ✅ means the doc exists and matches the code today.

- [x] README.md: overview, quickstart, layout
- [x] docs/PRODUCT.md, docs/ARCHITECTURE.md, docs/PIPELINE.md
- [x] docs/SERPAPI_USAGE.md (doubles as the submission's SerpApi explanation)
- [x] docs/DATA_MODEL.md, docs/API.md, docs/DEVELOPMENT.md
- [x] docs/decisions/ ADR 0001–0008
- [ ] docs/spikes/S-01 filled with real findings
- [ ] Screenshots / GIF in README
- [ ] Final pass: every endpoint in API.md shows its real status

---

## Submission (SUB)

From [HACKATHON_BRIEF.md](HACKATHON_BRIEF.md#submission-checklist); details in [docs/SUBMISSION.md](docs/SUBMISSION.md).

- [ ] Choose a license (MIT suggested) and add `LICENSE`
- [ ] Public GitHub repo; secrets scan (no keys in history)
- [ ] Fresh-clone test: `make setup && make demo` works with no `.env`
- [ ] **First submit by Thu Oct 8** (timestamp locks on first submit; edits allowed after)
- [ ] Demo video under 3 min, running locally, opens in incognito
- [ ] Project description, SerpApi usage explanation (from docs/SERPAPI_USAGE.md)
- [ ] Disclosures: new project; AI tools used (Claude Code, Gemini); community source = BangPypers (confirm)
- [ ] Track: Commerce & Market Intelligence
- [ ] Teammates added (name + email), all of whom contributed
- [ ] Tick: rules, terms, links tested in incognito
