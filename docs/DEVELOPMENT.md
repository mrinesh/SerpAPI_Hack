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
make demo      # backend + frontend in replay mode with the demo profiles: no keys, no searches
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
| `SERPAPI_RUN_BUDGET` | `45` | Live searches allowed per pipeline run |
| `SERPAPI_CACHE_TTL_HOURS` | `72` | How long a cached search is reused |
| `SERPAPI_TIMEOUT_S` | `60` | Per-request timeout; some searches took over 30 s in S-01 |
| `SERPAPI_LOCATION` | `Bengaluru,Karnataka,India` | SerpApi `location` parameter |
| `DEEPSEEK_API_KEY` | – | Needed for `live` / `record` LLM mode only |
| `LLM_MODE` | `replay` | Same three modes, for DeepSeek |
| `DEEPSEEK_MODEL` | `deepseek-v4-pro` | Scoring, explanations, summaries (thinking on) |
| `DEEPSEEK_MODEL_LITE` | `deepseek-v4-pro` | High-volume field extraction (thinking off) |
| `DEEPSEEK_MAX_TOKENS` | `16384` | Completion cap per call, thinking included |
| `DEEPSEEK_TIMEOUT_S` | `120` | Per-request timeout; thinking replies take several seconds |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible endpoint |
| `AREA_INTEL_TTL_HOURS` | `168` | How long locality intelligence is reused |
| `ALERT_CHECK_INTERVAL_MINUTES` | `360` | Positive interval for scheduled profile refreshes |
| `SCHEDULER_ENABLED` | `false` | Run scheduled alert checks (spends live searches) |
| `DATABASE_URL` | SQLite file at `backend/data/realty_intel.db` | Any SQLAlchemy URL |

### Provider modes

| Mode | Network | Writes | Use for |
|---|---|---|---|
| `replay` | never | – | Demo, tests, judges, UI work |
| `live` | yes, through cache and budget | DB cache | Normal development with a key |
| `record` | yes | DB cache **and** `backend/fixtures/` | Capturing demo data to commit |

A request with no fixture in `replay` mode fails with `503 replay_miss`; record it once with a key.
`record` mode serves an existing fixture before spending anything (SerpApi and DeepSeek alike),
so re-recording a demo pays only for new requests. Delete a fixture file to refresh it.

## Commands

| Command | Does |
|---|---|
| `make setup` | Install everything, create `.env` |
| `make dev` | Backend (:8000) + frontend (:5173) with your `.env` modes |
| `make demo` | Same, forced to replay mode, with the two demo profiles added if missing (`SEED_DEMO_PROFILES=true`) |
| `make record` | Backend in record mode (spends searches; commit the new fixtures) |
| `make backend` / `make frontend` | Run one side |
| `make test` | Backend tests (pytest), frontend typecheck and tests (vitest) |
| `make lint` | ruff, ruff format check, eslint, tsc |
| `make fmt` | Auto-format and fix the backend |
| `make types` | Export OpenAPI and regenerate `frontend/src/api/schema.d.ts` |
| `make fixtures` | Run the tests and list committed recordings nothing uses (see [Keeping fixtures clean](#keeping-fixtures-clean)) |
| `make reset-db` | Delete the local SQLite database (recreated on next start; also clears the search ledger) |

## Conventions

**Backend**
- Dependencies point one way: `api → services → pipeline → integrations`.
- Only `integrations/serpapi/gateway.py` imports `serpapi`; only `integrations/llm/` imports
  `openai`.
- Investor-facing facts are `Sourced[T]`. Numbers are computed in code, never by the LLM.
- Prompts live in `integrations/llm/prompts/<task>.md`, not in Python strings.
- Unbuilt code raises `NotImplementedYet("<CHECKLIST ID>", "<what>")`.
- ruff (line length 100) is the formatter and linter; CI fails on either.

**Frontend**
- Response types come from `src/api/schema.d.ts` (generated), never hand-written.
- Form choices (property types, localities, goals...) come from `GET /api/meta/profile-options`,
  never hard-coded.
- Pure logic (money conversion, form validation) lives in `.ts` files with `*.test.ts` beside them.
- All HTTP goes through `src/api/client.ts`; data fetching through TanStack Query hooks.
- One file per route in `src/pages`; shared pieces in `src/components`.

**Git**
- Small commits; message says what and why. Reference checklist IDs (`F-02: parse prices`).
- Never commit `.env`, keys, or `backend/data/`. Fixtures are committed on purpose.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request: `make setup`, `make lint`,
`make test`, `npm run build` and `make fixtures`. It needs no secrets: everything replays from
the committed recordings. A red build on `main` blocks merging further branches.

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

## One-off searches

The developer CLI sends a single search through the gateway, so modes, cache and budget apply:

```bash
cd backend
uv run python -m app.cli budget                                  # used this month, left on account
SERPAPI_MODE=record uv run python -m app.cli serp google q="flat for sale in Hebbal Bangalore"
uv run python -m app.cli serp google_maps q="flats for sale Hebbal Bangalore"
uv run python scripts/s01_analyze.py                             # tabulate recorded Google results
```

Engine defaults (location, `gl`, `hl`, domain) come from `engines.py`; extra `key=value` pairs
override them. In `record` mode the response is saved under `backend/fixtures/serpapi/`; commit it.

## Discovery runs and replay

In `replay` mode a run only succeeds for searches that were recorded. These profiles replay
fully from the S-01 fixtures: apartment in Whitefield up to ₹80 L (Google + Maps), and office
space in Koramangala up to ₹3 Cr. Other profiles report "No recorded … response" for each
missing search; record them in `record` mode first.

F-03 also needs LLM fixtures for the exact criteria and candidate evidence. Committed
recordings cover both demo profiles (defined once in `app/reference/demo_profiles.py`), for the
first `VERIFY_MAX_CANDIDATES` (16) candidates of each run. A replay miss, such as a new profile
or a prompt change, marks verification failed while keeping discovered candidates visible, and
`tests/integration/test_demo_replay.py` fails. To re-record (needs `DEEPSEEK_API_KEY`):

```bash
cd backend
uv run python scripts/record_verification.py --profile residential
uv run python scripts/record_verification.py --profile commercial
```

These scripts force SerpApi replay and DeepSeek record, use a temporary isolated database,
and write validated LLM fixtures. They spend DeepSeek calls only, about 30 seconds per candidate.
After a prompt or input change, re-record, then run `make fixtures` and prune what it lists.
Residential criteria:
Whitefield apartment, max ₹80 L, rental income, 3% target, balanced risk, no must-haves or size
limits. Commercial criteria: Koramangala office, max ₹3 Cr, business type `IT services`, 6%
target, same goal and risk. Both targets are the wizard's suggestions (ADR 0018), so in the demo
you accept the suggested value. Other criteria require their own recordings. No fake LLM responses are shipped
as real provider recordings; tests generate fake responses in temporary fixture directories.

### Keeping fixtures clean

Every committed recording must be read by a test or a demo flow, so stale ones do not pile up
after a re-recording. `make fixtures` runs the test suite with a usage tracker
(`tests/fixture_usage.py`) and lists what nothing read; a fixture also counts as used when a test
or script names its file.

- **LLM recordings** that nothing uses fail the check. They are superseded responses: after a
  prompt or input change the request key changes and the old file is never read again. Delete
  them with `uv run python scripts/check_fixtures.py --prune` and commit the deletion with the
  new recordings.
- **SerpApi recordings** are only reported. Each cost a search, and the S-01 ones are the spike's
  evidence, so they are never deleted automatically.
- A recording a real flow uses but no test covers is a missing test, not an orphan: add the test.

## Known tooling issues

- **npm 10.9 cannot add vitest ≥ 4** (`Cannot read properties of null (reading 'edgesOut')`, an
  npm bug). Installing from the committed lockfile works on npm 10. To add or upgrade frontend
  dev dependencies, use npm 11 for that one command: `npx npm@11 install -D <package>`.

## Knowledge graph

graphify keeps a knowledge graph of the code in `graphify-out/` for navigation. It is
**local only** (gitignored): its git hooks rebuild it after every commit and checkout, which made
the tracked copy show up as modified constantly. On a fresh clone, or after changing code,
run `graphify update .` (AST only, no API cost).

## Scheduled alerts (I-11)

Set `SCHEDULER_ENABLED=true` and optionally `ALERT_CHECK_INTERVAL_MINUTES=360`, then restart
the backend. The job starts after one interval, runs one check at a time and coalesces missed
ticks. It uses the same profile lock, provider modes, caches and search budget as Check now.
Failures are logged per profile. Leave it off for the usual replay demo and use Check now.
Run one backend process: this is an in-process scheduler. Shutdown stops future ticks; a
running check is allowed to finish.
