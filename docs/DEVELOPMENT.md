# Development Guide

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | via uv |
| [uv](https://docs.astral.sh/uv/) | 0.9+ | `brew install uv` |
| Node.js | 22 or 24 LTS (20.19+ works) | <https://nodejs.org>; odd releases like 23 give engine warnings |
| make | any | preinstalled on macOS / Linux |

## Setup

```bash
make setup     # uv sync + npm install + creates .env from .env.example
make demo      # backend + frontend in replay mode: no keys, no searches spent
```

Open <http://localhost:5173>. API docs: <http://localhost:8000/docs>.

## Configuration

Settings live in `backend/app/config.py` and are read from `.env` at the repo root. Real
environment variables override `.env`.

| Variable | Default | Meaning |
|---|---|---|
| `SERPAPI_API_KEY` | – | Needed for `live` / `record` mode only |
| `SERPAPI_MODE` | `replay` | `live` · `record` · `replay` (see below) |
| `SERPAPI_MONTHLY_BUDGET` | `250` | Live searches allowed per calendar month |
| `SERPAPI_RUN_BUDGET` | `40` | Live searches allowed per pipeline run |
| `SERPAPI_CACHE_TTL_HOURS` | `72` | How long a cached search is reused |
| `SERPAPI_LOCATION` | `Bengaluru,Karnataka,India` | SerpApi `location` parameter |
| `GEMINI_API_KEY` | – | Needed for `live` / `record` LLM mode only |
| `LLM_MODE` | `replay` | Same three modes, for Gemini |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Scoring, explanations, summaries |
| `GEMINI_MODEL_LITE` | `gemini-3.5-flash-lite` | High-volume field extraction |
| `AREA_INTEL_TTL_HOURS` | `168` | How long locality intelligence is reused |
| `SCHEDULER_ENABLED` | `false` | Run scheduled alert checks (spends live searches) |
| `DATABASE_URL` | SQLite file at `backend/data/realty_intel.db` | Any SQLAlchemy URL |

### Provider modes

| Mode | Network | Writes | Use for |
|---|---|---|---|
| `replay` | never | – | Demo, tests, judges, UI work |
| `live` | yes, through cache and budget | DB cache | Normal development with a key |
| `record` | yes | DB cache **and** `backend/fixtures/` | Capturing demo data to commit |

A request with no fixture in `replay` mode fails with `503 replay_miss`; record it once with a key.

## Commands

| Command | Does |
|---|---|
| `make setup` | Install everything, create `.env` |
| `make dev` | Backend (:8000) + frontend (:5173) with your `.env` modes |
| `make demo` | Same, forced to replay mode |
| `make record` | Backend in record mode (spends searches; commit the new fixtures) |
| `make backend` / `make frontend` | Run one side |
| `make test` | Backend tests + frontend typecheck |
| `make lint` | ruff, ruff format check, eslint, tsc |
| `make fmt` | Auto-format and fix the backend |
| `make types` | Export OpenAPI and regenerate `frontend/src/api/schema.d.ts` |
| `make reset-db` | Delete the local SQLite database (recreated on next start) |

## Conventions

**Backend**
- Dependencies point one way: `api → services → pipeline → integrations`.
- Only `integrations/serpapi/gateway.py` imports `serpapi`; only `integrations/llm/` imports
  `google.genai`.
- Investor-facing facts are `Sourced[T]`. Numbers are computed in code, never by the LLM.
- Prompts live in `integrations/llm/prompts/<task>.md`, not in Python strings.
- Unbuilt code raises `NotImplementedYet("<CHECKLIST ID>", "<what>")`.
- ruff (line length 100) is the formatter and linter; CI fails on either.

**Frontend**
- Response types come from `src/api/schema.d.ts` (generated), never hand-written.
- All HTTP goes through `src/api/client.ts`; data fetching through TanStack Query hooks.
- One file per route in `src/pages`; shared pieces in `src/components`.

**Git**
- Small commits; message says what and why. Reference checklist IDs (`F-02: parse prices`).
- Never commit `.env`, keys, or `backend/data/`. Fixtures are committed on purpose.

## Definition of done

A checklist item is ✅ only when **all** of these are true, in the same commit or PR:

1. The code works in `replay` mode, and in `live` mode if it calls a provider.
2. Tests cover the logic (pure functions exhaustively; I/O through fakes or fixtures).
3. `make lint` and `make test` pass.
4. [CHECKLIST.md](../CHECKLIST.md): boxes ticked, status updated.
5. Docs touched by the change are updated: [API.md](API.md) status column,
   [PIPELINE.md](PIPELINE.md), [DATA_MODEL.md](DATA_MODEL.md),
   [SERPAPI_USAGE.md](SERPAPI_USAGE.md) as relevant.
6. [CHANGELOG.md](../CHANGELOG.md) has a line under *Unreleased*.
7. A design choice someone could reasonably question gets an ADR in [decisions/](decisions/).

## Adding a feature: the usual path

1. Find its row in CHECKLIST.md and mark it 🟨.
2. Grep its ID to find the stubs (`grep -rn "F-05" backend frontend`).
3. Adjust schemas first if the shape changes, then `make types`.
4. Implement pipeline/service logic, then the route, then the UI.
5. Record fixtures for any new SerpApi or LLM call (`make record`), commit them.
6. Walk the definition of done.

## Knowledge graph

This repo keeps a graphify knowledge graph in `graphify-out/` for code navigation. After
changing code, run `graphify update .` (AST only, no API cost).
