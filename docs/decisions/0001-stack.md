# 0001. FastAPI + React (Vite, TypeScript) + SQLite

- **Status:** Accepted
- **Date:** 2026-10-03

## Context
Judges must be able to run the project locally from the README, the demo video must show it
running locally, and "technical complexity" is a judging criterion (thin Streamlit wrappers are
common in the gallery). The judging panel and four of five partner communities are Python-centric.
The SerpApi key cannot ship to the browser, so a backend is required.

## Decision
- Backend: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, managed with uv; official `serpapi`
  and `google-genai` SDKs; APScheduler for jobs.
- Frontend: React 19 + TypeScript (Vite), Tailwind CSS, React Router, TanStack Query,
  Leaflet with OpenStreetMap tiles (no maps API key).
- Storage: SQLite file; tables created on startup; no migrations during the hackathon.
- TypeScript pinned to 5.9 because typescript-eslint and openapi-typescript do not yet support 7.

## Consequences
- Two processes in development (`make dev` runs both); zero external services.
- Frontend types are generated from FastAPI's OpenAPI, so schemas are written once.
- Changing a table means deleting the local DB; acceptable for a hackathon, revisit after.
