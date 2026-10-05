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
- 2026-10-05 · F-03: DeepSeek relevance verification, implemented and tested offline.
  - Gap-only extraction with exact evidence, supported units/enums and original provenance.
  - Profile verification with deterministic constraint overrides, missing-data handling and
    explicit unverified ROI; rejected candidates retained with reasons.
  - Incremental stage progress, per-run snapshots and durable partial results on failure;
    `GET /api/runs/{id}/verifications` and run UI with a "Filtered out" view.
  - I-07: validated LLM DB cache and record/replay, keyed by task/model/tier/schema/prompt.
  - Recording script for residential/commercial demos using existing SerpApi fixtures.
    Live acceptance and committed LLM recordings remain pending: no key configured here.
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
