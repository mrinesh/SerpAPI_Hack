# Changelog

Notable changes, newest first. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Reference CHECKLIST IDs.

## [Unreleased]

### Added
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
