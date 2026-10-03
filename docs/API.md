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
| GET | `/meta/budget` | `BudgetStatus`: searches used, cache hits, account searches left | I-05 | 🧱 |
| GET | `/meta/profile-options?city=` | `ProfileOptions`: segments and property types, localities, goals with their ROI measure, risk levels, limits | F-01 | ✅ |
| POST | `/profiles` | `InvestorProfile` (201) | F-01 | ✅ |
| GET | `/profiles` | `InvestorProfile[]` | F-01 | ✅ |
| GET | `/profiles/{profile_id}` | `InvestorProfile` | F-01 | ✅ |
| PUT | `/profiles/{profile_id}` | `InvestorProfile` | F-01 | ✅ |
| DELETE | `/profiles/{profile_id}` | 204 | F-01 | ✅ |
| POST | `/profiles/{profile_id}/runs` | `PipelineRun` (202); poll the run | I-09 | 🧱 |
| GET | `/runs/{run_id}` | `PipelineRun` with `StageEvent[]` | I-09, F-20 | 🧱 |
| GET | `/runs/{run_id}/recommendations` | `Recommendation[]`, ranked | F-04 | 🧱 |
| GET | `/properties/{listing_id}` | `PropertyDetail` | F-07 | 🧱 |
| GET | `/areas/{locality_key}` | `AreaIntel`; key like `bengaluru/whitefield` | F-05 | 🧱 |
| GET | `/saved` | `SavedProperty[]` | F-08 | 🧱 |
| POST | `/saved` | `SavedProperty` (201) | F-08 | 🧱 |
| DELETE | `/saved/{listing_id}` | 204 | F-08 | 🧱 |
| GET | `/compare?ids=a&ids=b` | `CompareResult` (2–4 ids) | F-08 | 🧱 |
| GET | `/alerts?unread_only=` | `Alert[]` | F-10 | 🧱 |
| POST | `/alerts/check` | `Alert[]` newly created | F-10 | 🧱 |

## Frontend types

The frontend never hand-writes response types. After changing a schema:

```bash
make types   # exports backend/openapi.json and regenerates frontend/src/api/schema.d.ts
```
