# 0009. SQLite over DuckDB for the app database

- **Status:** Accepted
- **Date:** 2026-10-03

## Context
DuckDB came up as an alternative store. The app's workload is transactional: the pipeline thread
writes run status, progress events and listings while the UI polls run status about once a
second, and cached SerpApi and LLM responses are point lookups by key. Data volumes are small
(thousands of listings, hundreds of cached responses). DuckDB is a columnar engine built for
analytical scans, and while one process holds a DuckDB file for writing, no other process can
open it, even read-only. It also needs a third-party SQLAlchemy dialect.

## Decision
Keep SQLite as the application database, in WAL mode with `busy_timeout=5000` and
`foreign_keys=ON` set on every connection (`app/db/session.py`). Use DuckDB only as an optional,
ad-hoc tool for analysing recorded fixtures, e.g. `read_json('backend/fixtures/serpapi/google/*.json')`
during spike S-01; it is not an app dependency.

Storage is layered: raw SerpApi/LLM responses are kept verbatim and never edited; listings,
area intel and competitor reports are derived from them and can be rebuilt without new searches;
run results are per-run snapshots; profiles, saved properties and alerts are user data.

## Consequences
- Readers (UI, scripts, the sqlite3 CLI) work while the pipeline writes.
- Foreign keys are enforced, so deleting rows that others reference fails loudly instead of
  leaving orphans.
- Revisit only if analytical queries over large data become a real need.
