# API

Base path `/api`. Interactive docs at <http://localhost:8000/docs> while the backend runs.
Errors use one shape, `{"error": {"code", "message", "details"}}`; see
[ARCHITECTURE.md](ARCHITECTURE.md#error-contract).

Status: ✅ built · 🧱 scaffolded (returns `501 not_implemented` with the checklist ID).

Invalid input returns `422` with `details.fields`, a list of `{loc, msg}` where `loc` is like
`["body", "localities"]`. Schema errors and reference-data errors (unknown locality, unsupported
city) use the same shape.

| Method | Path | Returns | Feature | Status |
|---|---|---|---|---|
| GET | `/health` | `HealthStatus`: version, provider modes, city | I-01 | ✅ |
| GET | `/meta/budget` | `BudgetStatus`: searches used, cache hits, account searches left | I-05 | ✅ |
| GET | `/meta/profile-options?city=` | `ProfileOptions`: segments and property types, localities, goals with their ROI measure, risk levels, limits | F-01 | ✅ |
| POST | `/profiles` | `InvestorProfile` (201) | F-01 | ✅ |
| GET | `/profiles` | `InvestorProfile[]` | F-01 | ✅ |
| GET | `/profiles/{profile_id}` | `InvestorProfile` | F-01 | ✅ |
| PUT | `/profiles/{profile_id}` | `InvestorProfile` | F-01 | ✅ |
| DELETE | `/profiles/{profile_id}` | 204 | F-01 | ✅ |
| POST | `/profiles/{profile_id}/runs` | `PipelineRun` (202), started in the background; poll the run | I-09 | ✅ |
| GET | `/runs/{run_id}` | `PipelineRun` with `StageEvent[]`, searches used, cache hits | I-09, F-20 | ✅ |
| GET | `/runs/{run_id}/listings` | `Listing[]` the run discovered: priced entries cheapest first, then projects | F-02 | ✅ |
| GET | `/runs/{run_id}/verifications` | `Verification[]`: completed checks, including rejects and reasons | F-03 | ✅ |
| GET | `/runs/{run_id}/recommendations` | `Recommendation[]`, ranked | F-04 | 🧱 |
| GET | `/properties/{listing_id}` | `PropertyDetail` | F-07 | 🧱 |
| GET | `/areas/{locality_key}` | Latest shared `AreaIntel`; read-only, explicit stale state; 404 before enrichment | F-05 | ✅ |
| GET | `/runs/{run_id}/areas` | Run-specific `AreaIntel[]` snapshots with existing price benchmarks and section warnings | F-05 | ✅ |
| GET | `/saved` | `SavedProperty[]` | F-08 | 🧱 |
| POST | `/saved` | `SavedProperty` (201) | F-08 | 🧱 |
| DELETE | `/saved/{listing_id}` | 204 | F-08 | 🧱 |
| GET | `/compare?ids=a&ids=b` | `CompareResult` (2–4 ids) | F-08 | 🧱 |
| GET | `/alerts?unread_only=` | `Alert[]` | F-10 | 🧱 |
| POST | `/alerts/check` | `Alert[]` newly created | F-10 | 🧱 |

Run listings include grounded extraction additions and rejected candidates, from snapshots
within that run. Verification responses can be read while the run is active or after a failure;
an unchecked candidate has no verification yet. Both endpoints return 404 for an unknown run.
`verify` stage counts contain `candidates`, `checked`, `rejected`, `flagged` (too good to be true)
and `unchecked` (candidates past `VERIFY_MAX_CANDIDATES`, default 16, which have no verification).
Each `Verification.flags` entry is a `QualityFlag` (`kind`, `severity`, `reason`, ADR 0014).
F-04 ranking is still pending.

## Area intelligence (F-05)

Areas are produced during the enrich stage, once per discovered locality. Both GET endpoints
are read-only and never call external providers. A run created before F-05, or one still
enriching, may return an empty/partial list. Unknown runs return 404; unknown geography returns
422. Section failures return readable partial data with `warnings` and `section_status`, rather
than pretending failed requests were empty results. `stale` indicates that a new run should
refresh the area. Only run snapshots contain the existing per-property-type `price_levels`.

Schema, examples, cache behavior and diagnostics: [F-05 guide](F05_AREA_INTELLIGENCE.md).

## Frontend types

The frontend never hand-writes response types. After changing a schema:

```bash
make types   # exports backend/openapi.json and regenerates frontend/src/api/schema.d.ts
```
