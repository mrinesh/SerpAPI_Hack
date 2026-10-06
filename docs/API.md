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
| POST | `/profiles/target-suggestion` | `TargetSuggestion`: a sourced typical target ROI for segment, types, localities, goal and risk; `target_roi_pct` null when no data | F-01 / F-09 | ✅ |
| GET | `/profiles` | `InvestorProfile[]` | F-01 | ✅ |
| GET | `/profiles/{profile_id}` | `InvestorProfile` | F-01 | ✅ |
| PUT | `/profiles/{profile_id}` | `InvestorProfile` | F-01 | ✅ |
| DELETE | `/profiles/{profile_id}` | 204 | F-01 | ✅ |
| POST | `/profiles/{profile_id}/runs` | `PipelineRun` (202), started in the background; poll the run | I-09 | ✅ |
| GET | `/runs/{run_id}` | `PipelineRun` with `StageEvent[]`, searches used, cache hits | I-09, F-20 | ✅ |
| GET | `/runs/{run_id}/listings` | `Listing[]` the run discovered: priced entries cheapest first, then projects | F-02 | ✅ |
| GET | `/runs/{run_id}/verifications` | `Verification[]`: completed checks, including rejects and reasons | F-03 | ✅ |
| GET | `/runs/{run_id}/recommendations` | `Recommendation[]`, ranked; empty until the rank stage runs | F-04 | ✅ |
| GET | `/properties/{listing_id}` | `PropertyDetail` | F-07 | 🧱 |
| GET | `/areas/{locality_key}` | `AreaIntel`; key like `bengaluru/whitefield`; 404 if never built | F-05 | ✅ |
| GET | `/runs/{run_id}/areas` | `AreaIntel[]` for the localities of the run's ranked candidates | F-05 | ✅ |
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
`AreaIntel.section_status` / `warnings` say which area sections failed and why; enrich stage
counts add `area_warnings`. `InvestmentMetrics.target_roi_pct` is the target the verdict used,
and `assessment_note` explains a missing verdict (ADR 0019). A corrupt cached area makes
`GET /areas/{key}` return 500 `internal_error` with `details.operation = "area_cache_read"`.
`rank` stage counts contain `ranked` and `explained` (AI reasons that passed the number check).

## Frontend types

The frontend never hand-writes response types. After changing a schema:

```bash
make types   # exports backend/openapi.json and regenerates frontend/src/api/schema.d.ts
```
