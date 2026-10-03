# Graph Report - SerpAPI_Hack  (2026-10-03)

## Corpus Check
- 133 files · ~28,003 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 8, .example 1, .lock 1)

## Summary
- 779 nodes · 1471 edges · 67 communities (42 shown, 25 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 178 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7f473053`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SerpApi India Hackathon 2026 — Working Brief
- CHECKLIST.md
- docs/README.md
- views.py
- types.ts
- NotImplementedYet
- SerpEngine
- Features
- InvestorProfile
- ModelTier
- decisions/README.md
- models.py
- compilerOptions
- main.py
- compilerOptions
- package.json
- scheduler.py
- engines.py
- conftest.py
- services/alerts.py
- devDependencies
- Settings
- query_planner.py
- Development Guide
- Product
- Realty Intel *(working name)*
- SerpApi Usage
- deps.py
- Architecture
- S-01 · Data coverage spike (Bengaluru)
- 0008-code-computes-llm-explains.md
- Pipeline
- dependencies
- scripts
- Added
- schema.d.ts
- 0002-serpapi-as-the-only-listing-source.md
- 0004-provenance-on-every-field.md
- Data Model
- Hackathon Submission
- vite.config.ts
- errors.py
- tsconfig.json
- engines
- realty-intel-backend
- Recommendation

## God Nodes (most connected - your core abstractions)
1. `NotImplementedYet` - 64 edges
2. `SerpEngine` - 24 edges
3. `Settings` - 23 edges
4. `Listing` - 22 edges
5. `compilerOptions` - 20 edges
6. `InvestorProfile` - 18 edges
7. `PipelineContext` - 17 edges
8. `compilerOptions` - 17 edges
9. `Base` - 16 edges
10. `AreaIntel` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Added` --references--> `cache_key()`  [INFERRED]
  CHANGELOG.md → backend/app/integrations/serpapi/gateway.py
- `Consequences` --references--> `cache_key()`  [INFERRED]
  docs/decisions/0003-record-replay-and-search-budget.md → backend/app/integrations/serpapi/gateway.py
- `I-02 SerpApi gateway · P0 · 🧱` --references--> `AppError`  [INFERRED]
  CHECKLIST.md → backend/app/core/errors.py
- `Staying inside the free tier (250 searches / month)` --references--> `google_trends()`  [INFERRED]
  docs/SERPAPI_USAGE.md → backend/app/integrations/serpapi/engines.py
- `Tables` --references--> `cache_key()`  [INFERRED]
  docs/DATA_MODEL.md → backend/app/integrations/serpapi/gateway.py

## Import Cycles
- None detected.

## Communities (67 total, 25 thin omitted)

### Community 0 - "SerpApi India Hackathon 2026 — Working Brief"
Cohesion: 0.20
Nodes (10): Hard constraints, IP / legal worth knowing, Judges — all SerpApi staff, mostly developer advocates, Landscape — BuiltWithSerpApi gallery (179 public projects, theme counts), Prizes — ₹2,10,000 cash + 120,000 credits competitive, ₹3L+ total value, SerpApi India Hackathon 2026 — Working Brief, Six tracks (pick exactly one; SerpApi may reclassify), Strategic reads (+2 more)

### Community 1 - "CHECKLIST.md"
Cohesion: 0.31
Nodes (4): Code rules, Documentation discipline (required), graphify, Realty Intel: real estate investor intelligence on SerpApi

### Community 2 - "docs/README.md"
Cohesion: 0.27
Nodes (4): Backend, API, Frontend types, Documentation

### Community 3 - "views.py"
Cohesion: 0.06
Nodes (39): get_area(), get_property(), get_competitor_report(), compute_metrics(), flag_listing(), extract(), ExtractedField, ExtractedListing (+31 more)

### Community 4 - "types.ts"
Cohesion: 0.05
Nodes (42): Frontend, ApiError, ApiErrorBody, apiFetch(), useHealth(), Alert, AreaIntel, BudgetStatus (+34 more)

### Community 5 - "NotImplementedYet"
Cohesion: 0.07
Nodes (25): get_budget(), compare(), list_saved(), save(), unsave(), NotImplementedYet, canonical_url(), detect_portal() (+17 more)

### Community 6 - "SerpEngine"
Cohesion: 0.19
Nodes (8): cache_key(), SerpResponse, SerpEngine, Recorded fixtures, test_key_depends_on_engine(), test_key_ignores_api_key_and_none(), test_key_ignores_param_order(), I-02 SerpApi gateway · P0 · 🧱

### Community 7 - "Features"
Cohesion: 0.06
Nodes (35): run_pipeline(), Docs (D-01), F-01 Investor profile · P0 · 🧱, F-04 Ranked recommendations · P0 · 🧱, F-06 Competitor analysis (commercial) · P0 · 🧱, F-07 Property detail page · P0 · 🧱, F-08 Saved and compare · P1 · 🧱, F-09 Investment metrics · P0 · 🧱 (+27 more)

### Community 8 - "InvestorProfile"
Cohesion: 0.12
Nodes (18): create_profile(), get_profile(), list_profiles(), start_run(), update_profile(), InvestmentGoal, InvestorProfile, InvestorProfileIn (+10 more)

### Community 9 - "ModelTier"
Cohesion: 0.11
Nodes (7): ProviderMode, LLMProvider, ModelTier, get_llm(), GeminiProvider, RecordingLLM, Decision

### Community 10 - "decisions/README.md"
Cohesion: 0.06
Nodes (24): Consequences, Context, Decision, NNNN. Title, 0001. FastAPI + React (Vite, TypeScript) + SQLite, Consequences, Context, Decision (+16 more)

### Community 11 - "models.py"
Cohesion: 0.13
Nodes (14): Base, new_id(), utcnow(), AlertRow, AreaIntelRow, CompetitorReportRow, ListingRow, LlmCacheRow (+6 more)

### Community 12 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+13 more)

### Community 13 - "main.py"
Cohesion: 0.17
Nodes (6): get_settings(), get_db(), init_db(), start_scheduler(), create_app(), lifespan()

### Community 14 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+10 more)

### Community 15 - "package.json"
Cohesion: 0.14
Nodes (16): name, private, type, version, eslint, @eslint/js, eslint-plugin-react-hooks, globals (+8 more)

### Community 16 - "scheduler.py"
Cohesion: 0.24
Nodes (3): configure_logging(), run_alert_check(), shutdown_scheduler()

### Community 17 - "engines.py"
Cohesion: 0.19
Nodes (7): google_maps_reviews(), google_maps_search(), google_news(), google_search(), google_trends(), Engines and their roles, SerpApi usage

### Community 19 - "services/alerts.py"
Cohesion: 0.27
Nodes (5): check_alerts(), list_alerts(), Alert, check_alerts(), list_alerts()

### Community 20 - "devDependencies"
Cohesion: 0.13
Nodes (15): devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, globals, openapi-typescript, tailwindcss, @tailwindcss/vite (+7 more)

### Community 22 - "Settings"
Cohesion: 0.22
Nodes (4): Settings, SerpApiGateway, PipelineContext, get_area_intel()

### Community 23 - "query_planner.py"
Cohesion: 0.33
Nodes (5): fetch_hits(), plan_queries(), PlannedQuery, RawSearchHit, F-02 Property discovery · P0 · 🧱

### Community 24 - "Development Guide"
Cohesion: 0.20
Nodes (10): Adding a feature: the usual path, Commands, Configuration, Conventions, Definition of done, Development Guide, Knowledge graph, Prerequisites (+2 more)

### Community 25 - "Product"
Cohesion: 0.20
Nodes (10): Core value, End-to-end flow, Features, Hackathon framing, One-liner, Problem, Product, Risks and how the design answers them (+2 more)

### Community 26 - "Realty Intel *(working name)*"
Cohesion: 0.25
Nodes (8): AI disclosure, Architecture, Documentation, Quickstart, Realty Intel *(working name)*, Repository layout, What it does, Why

### Community 27 - "SerpApi Usage"
Cohesion: 0.33
Nodes (6): Cost model *(estimate; confirmed in S-03)*, Data handling, SDK, SerpApi Usage, Staying inside the free tier (250 searches / month), Why the product needs search data

### Community 28 - "deps.py"
Cohesion: 0.09
Nodes (10): health(), get_recommendations(), get_run(), start_run(), PipelineRun, PipelineStage, RunStatus, StageEvent (+2 more)

### Community 29 - "Architecture"
Cohesion: 0.25
Nodes (8): Architecture, Configuration, Directory map, Error contract, Key design rules, Layers, Request lifecycle: a pipeline run, System overview

### Community 30 - "S-01 · Data coverage spike (Bengaluru)"
Cohesion: 0.25
Nodes (7): Decisions, Enrichment engines, Field availability (share of single-listing hits), Findings per portal, Queries run, S-01 · Data coverage spike (Bengaluru), Setup

### Community 31 - "0008-code-computes-llm-explains.md"
Cohesion: 0.40
Nodes (4): 0008. Code computes scores and money; the LLM extracts and explains, Consequences, Context, Decision

### Community 32 - "Pipeline"
Cohesion: 0.29
Nodes (7): 1 · Plan (`query_planner.py`, F-02), 2 · Fetch (`discovery.py`, F-02), 3 · Clean (`cleaning.py`, F-02), 5 · Enrich (`enrichment/`, `metrics.py`, F-05, F-06, F-09), 6 · Rank (`ranking.py`, F-04), LLM calls per run, Pipeline

### Community 33 - "dependencies"
Cohesion: 0.29
Nodes (7): dependencies, leaflet, react, react-dom, react-leaflet, react-router, @tanstack/react-query

### Community 34 - "scripts"
Cohesion: 0.29
Nodes (7): scripts, build, dev, gen:types, lint, preview, typecheck

### Community 35 - "Added"
Cohesion: 0.67
Nodes (3): Added, Changelog, [Unreleased]

### Community 36 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 38 - "0002-serpapi-as-the-only-listing-source.md"
Cohesion: 0.40
Nodes (4): 0002. SerpApi is the only listing source; no portal scraping, Consequences, Context, Decision

### Community 39 - "0004-provenance-on-every-field.md"
Cohesion: 0.40
Nodes (4): 0004. Every investor-facing fact carries source and confidence, Consequences, Context, Decision

### Community 40 - "Data Model"
Cohesion: 0.67
Nodes (3): Changing the model, Data Model, Provenance: `Sourced[T]`

### Community 41 - "Hackathon Submission"
Cohesion: 0.50
Nodes (4): Demo video plan (< 3 min, running locally), Form fields, Hackathon Submission, Pre-submit checks

### Community 42 - "vite.config.ts"
Cohesion: 0.50
Nodes (3): @tailwindcss/vite, vite, @vitejs/plugin-react

### Community 43 - "errors.py"
Cohesion: 0.15
Nodes (6): AppError, NotFound, register_exception_handlers(), ReplayMiss, SearchBudgetExceeded, I-03 SerpApi record / replay · P0 · 🧱

### Community 73 - "Recommendation"
Cohesion: 0.29
Nodes (3): Explanation, rank(), Recommendation

## Knowledge Gaps
- **226 isolated node(s):** `realty-intel-backend`, `name`, `private`, `version`, `type` (+221 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 385 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NotImplementedYet` connect `NotImplementedYet` to `views.py`, `SerpEngine`, `Features`, `InvestorProfile`, `ModelTier`, `Recommendation`, `errors.py`, `services/alerts.py`, `Settings`, `query_planner.py`, `deps.py`?**
  _High betweenness centrality (0.175) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `NotImplementedYet` (e.g. with `GeminiProvider` and `RecordingLLM`) actually correct?**
  _`NotImplementedYet` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `SerpEngine` (e.g. with `google_maps_reviews()` and `google_maps_search()`) actually correct?**
  _`SerpEngine` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `Settings` (e.g. with `get_llm()` and `GeminiProvider`) actually correct?**
  _`Settings` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `Listing` (e.g. with `normalize_hits()` and `compute_metrics()`) actually correct?**
  _`Listing` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `realty-intel-backend`, `name`, `private` to the rest of the system?**
  _226 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `views.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05721003134796238 - nodes in this community are weakly interconnected._