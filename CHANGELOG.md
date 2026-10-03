# Changelog

Notable changes, newest first. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Reference CHECKLIST IDs.

## [Unreleased]

### Added
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
- 2026-10-03 · ROI is one target compared against the goal's measure: rental yield, price growth
  or total return. Net yield and cap rate removed (ADR 0010).
- 2026-10-03 · Property types now follow the listing portals' categories; bedrooms dropped from
  the profile; `business_category` renamed `business_type`.
- 2026-10-03 · Bengaluru localities cut to the 15 found on Wikipedia's neighbourhood list.
- 2026-10-03 · SQLite runs in WAL mode with `busy_timeout` and foreign keys (ADR 0009).
- 2026-10-03 · All 422 responses use the shared error shape with `details.fields`.
