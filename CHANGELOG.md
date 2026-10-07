# Changelog

Notable changes, newest first. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Reference CHECKLIST IDs.

## [Unreleased]

### Changed
- 2026-10-05 · I-06: DeepSeek V4 Pro replaces Gemini (ADR 0012). `DeepSeekProvider` uses the
  `openai` SDK against the OpenAI-compatible API: JSON-mode structured output validated with
  Pydantic and retried once, thinking on for the reasoning tier and off for lite extraction.
  `DEEPSEEK_*` settings replace `GEMINI_*`; `python -m app.cli llm` checks connectivity.
  Tests no longer read `.env`, so they cannot pick up real API keys.

### Added
- 2026-10-07 · Submission prep (I-13, SUB): `make demo` seeds the two recorded demo profiles
  (`SEED_DEMO_PROFILES`), so a fresh clone opens with searches that replay; MIT `LICENSE`;
  README rewritten to match what is built, with screenshots; form text and video plan in
  docs/SUBMISSION.md. Fresh-clone test and a secrets scan of every branch's history passed.
- 2026-10-07 · Competitor analysis (F-06, ADR 0023): commercial runs search Google Maps for the
  profile's business at each locality centre, keep places within 2 km, and show density, a
  density level, average rating and review volume, read as competition for shops and as a
  business cluster for offices, warehouses and land. Card beside the area card, a layer on both
  maps, `GET /runs/{id}/competitors`, and `PropertyDetail.competitors`. Display only; ranks are
  unchanged. Recorded for the commercial demo with 1 search.
- 2026-10-07 · Results map (F-19, ADR 0022): the run page maps every candidate on OpenStreetMap,
  ranked ones numbered and coloured by score, at their own Google Maps GPS or grouped in one
  dashed marker at the locality centre (never an invented point), with filtered-out and
  metro / school / hospital overlays. The detail page maps the property with its area's
  amenities. Frontend only; 0 searches, 0 LLM calls.
- 2026-10-07 · Property detail page (F-07, ADR 0021): `GET /properties/{id}?run_id=` returns the
  listing as one run judged it (verification, rank and reasons, metrics, the run's area, price
  across runs, every source), from stored results only. The page at
  `/runs/:runId/properties/:listingId`, linked from every run card, shows each fact with a
  confidence badge and its sources (`SourcedValue`, F-11), flag chips (F-12) and a "Where this
  came from" list. 0 searches, 0 LLM calls.
- 2026-10-07 · Locality news and frozen per-run areas, adapted from gscode007's `f-05` branch
  (ADR 0020): Google News per locality, kept when it names the locality, one article per event,
  10 newest, labelled by DeepSeek lite for topic and sentiment; shown in the area panel and not
  scored. Each run now freezes the areas it used (`run_area_intel`). The teammate's recorded
  news searches are reused (0 searches; 2 lite calls). Demo results unchanged.
- 2026-10-07 · Hardening F-05 / F-09, adapted from gscode007's parallel `f-05` / `f-09` branches
  (ADR 0019): area sections record ok / empty / failed with typed warnings, shown in the run
  stage and the area panel instead of silently missing data; a partial area expires at once so
  the next run retries; the area cache is reused only when it parses and matches the schema
  version and provider modes; metrics are withheld for starting / range prices as well as
  implausible ones, and store the target they used plus a reason when there is no verdict.
  Recorded demo results are unchanged.
- 2026-10-06 · Suggested target ROI (F-01 / F-09): the wizard's Money step fills a target from
  the market's sourced typical value of the goal's measure (area yield; average yearly growth
  from a quoted multi-year change; or both), adjusted for risk and rounded to 0.5%. Fills only an
  empty or still-suggested field (ADR 0018). `POST /api/profiles/target-suggestion`. Demo
  targets are now the suggestions (Whitefield 3%, Koramangala 6%); demos re-recorded.
- 2026-10-06 · F-09 investment metrics: rental yield before costs from a quoted area rent
  (median of ≥ 3 checked rent ÷ size pairs per locality and type), price growth (investor
  override or the area's past 12 months), total return, price per sq ft vs the area, and
  `meets_target_roi` for the goal's measure. Fills F-04's `roi` score proportionally (full marks
  at 1.5× target); missing the target lowers the score, never filters (ADR 0017). Cards show
  yield, growth, total and a target badge; the area panel shows rent. Recorded: Whitefield flats
  ₹32.5/sq ft/month (Sowparnika 4.76%, meets 4%), Koramangala offices ₹84.4 (6.4–7.2%).
- 2026-10-06 · F-05 area intelligence: geocoded locality centre (I-12), nearest metro stations,
  schools and hospitals from Google Maps with distances computed in code, past-12-month price
  growth from a quoted snippet (validated), and number-checked AI summaries; cached per
  locality for 7 days. Fills F-04's `area` score with amenity access (ADR 0016).
  `GET /api/runs/{id}/areas`, `GET /api/areas/{key}`, area panel on the run page. Recorded for
  both demos: Whitefield +29%, metro 1.8 km; Koramangala +26.9%, metro 2.7 km. News and
  Trends deferred.
- 2026-10-06 · F-04 ranked recommendations: composite score in code from relevance, value
  against the locality price level and evidence, weighted by goal and risk appetite, minus
  flag penalties (ADR 0015); ROI and area signals reserved for F-09 / F-05. Code reasons for
  every pick; DeepSeek reasons for the top 5, with every number checked against the figures
  given. `GET /api/runs/{id}/recommendations`; "Recommended" tab with a score breakdown.
  Recorded for both demos (9 lite calls, no searches).
- 2026-10-06 · F-12 price flags (part): too-good-to-be-true against a per-locality price level
  from a live Google search, read by DeepSeek with a validated quote; run-median fallback, no flat
  rate (ADR 0014). Missing price/size flags; flag chips on run cards. A high flag caps at weak.
  Recorded for both demos (2 searches, 2 lite calls): the ₹3.6 L Koramangala "sale" at ₹75/sq ft
  is now flagged against ₹17,501/sq ft. Record mode in both gateways reuses existing fixtures.
- 2026-10-06 · F-03 / I-07 complete: live DeepSeek recordings committed for both demo profiles
  (residential: first 16 of 28 candidates; commercial: all 6); both replay with no key.
  - `VERIFY_MAX_CANDIDATES` (default 16) caps checks per run; the rest are reported `unchecked`.
  - Prompt files no longer start with a BOM, and prompts are read as `utf-8-sig`, so an editor
    BOM cannot change LLM cache keys. The uncertainty cap in `verify` no longer depends on list
    order. `tests/integration/test_demo_replay.py` fails whenever recordings go stale.
- 2026-10-05 · F-03: DeepSeek relevance verification, implemented and tested offline.
  - Gap-only extraction with exact evidence, supported units/enums and original provenance.
  - Profile verification with deterministic constraint overrides, missing-data handling and
    explicit unverified ROI; rejected candidates retained with reasons.
  - Incremental stage progress, per-run snapshots and durable partial results on failure;
    `GET /api/runs/{id}/verifications` and run UI with a "Filtered out" view.
  - I-07: validated LLM DB cache and record/replay, keyed by task/model/tier/schema/prompt.
  - Recording script for residential/commercial demos using existing SerpApi fixtures.
- 2026-10-04 · F-02: property discovery, end to end.
  - SerpApi gateway (I-02–I-04): replay / live / record, DB cache with TTL, per-run and monthly
    budgets, search ledger, error mapping. `GET /api/meta/budget` + header chip (I-05).
  - S-01 data-coverage spike: 24 searches, 23 recorded as fixtures; findings and ADR 0011.
  - Discovery: tested query templates, portal-page snippet parsing, Google Maps projects,
    candidates with stable ids and per-run observations.
  - Background runs with live stage progress (I-09, F-20); run page with priced entries and
    projects.
  - `app/cli.py` (one-off searches, budget) and `scripts/s01_analyze.py`.
- 2026-10-03 · F-01: investor profiles, end to end.
  - API: profile CRUD including `DELETE`, `GET /api/meta/profile-options`, and checks against
    reference data (supported city, known localities).
  - UI: profiles page and a 3-step wizard (What → Where → Money) with lakh/crore budgets,
    per-step validation and server errors mapped back to their fields.
  - Tests: 25 schema, 8 API and 15 frontend (vitest) cases.
- 2026-10-03 · I-01: project framework.
  - Backend: FastAPI app factory, settings with provider modes, error contract (501 carries the
    checklist ID), SQLite tables, Pydantic domain schemas with `Sourced[T]` provenance, SerpApi
    gateway skeleton with stable `cache_key`, engine parameter builders, Gemini provider and
    record/replay skeletons, prompt placeholders, one module per pipeline stage, services,
    routes, APScheduler wiring, Bengaluru locality reference data.
  - Frontend: Vite + React + TypeScript + Tailwind shell, routes and placeholder pages for every
    screen, typed API client, generated OpenAPI types.
  - Docs: README, product, architecture, pipeline, SerpApi usage, data model, API, development
    guide, ADRs 0001–0008, S-01 spike template, submission notes, CHECKLIST.
  - Tooling: Makefile, `.env.example`, ruff, pytest (8 tests), eslint, tsc.

### Changed
- 2026-10-04 · Listings are discovered candidates (snippet entries, Maps projects); `listings` keyed
  by a stable identity hash, with price columns; new `listing_observations` (ADR 0011).
- 2026-10-04 · Google Search params drop `num` (not in SerpApi's docs); `SERPAPI_TIMEOUT_S`
  default 60 s (two S-01 searches exceeded 30 s).
- 2026-10-04 · Deleting a profile also deletes its runs, observations and alerts.
- 2026-10-04 · `graphify-out/` is gitignored and no longer tracked; the graph is rebuilt locally
  by graphify's hooks. `.gitattributes` (its merge rule) removed.
- 2026-10-03 · ROI is one target compared against the goal's measure: rental yield, price growth
  or total return. Net yield and cap rate removed (ADR 0010).
- 2026-10-03 · Property types now follow the listing portals' categories; bedrooms dropped from
  the profile; `business_category` renamed `business_type`.
- 2026-10-03 · Bengaluru localities cut to the 15 found on Wikipedia's neighbourhood list.
- 2026-10-03 · SQLite runs in WAL mode with `busy_timeout` and foreign keys (ADR 0009).
- 2026-10-03 · All 422 responses use the shared error shape with `details.fields`.
