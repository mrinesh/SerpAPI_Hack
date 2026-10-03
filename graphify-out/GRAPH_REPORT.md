# Graph Report - SerpAPI_Hack  (2026-10-03)

## Corpus Check
- 149 files · ~36,922 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 8, .example 1, .lock 1)

## Summary
- 954 nodes · 1927 edges · 83 communities (47 shown, 36 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 174 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cf9d6c0e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SerpApi India Hackathon 2026 — Working Brief
- Hackathon Submission
- docs/README.md
- verification.py
- types.ts
- routes/portfolio.py
- SerpEngine
- Features
- run.py
- NotImplementedYet
- decisions/README.md
- models.py
- compilerOptions
- Realty Intel: real estate investor intelligence on SerpApi
- compilerOptions
- package.json
- NNNN. Title
- Listing
- test_profiles_api.py
- test_profile_schema.py
- devDependencies
- 0008. Code computes scores and money; the LLM extracts and explains
- 0001. FastAPI + React (Vite, TypeScript) + SQLite
- 0006. Enrich per locality, not per property
- Development Guide
- Product
- Realty Intel *(working name)*
- Architecture
- S-01 · Data coverage spike (Bengaluru)
- 0002-serpapi-as-the-only-listing-source.md
- Pipeline
- dependencies
- scripts
- [Unreleased]
- schema.d.ts
- router.tsx
- listing.py
- 0009. SQLite over DuckDB for the app database
- routes/properties.py
- vite.config.ts
- main.py
- views.py
- tsconfig.json
- engines
- realty-intel-backend
- router.py
- reference/__init__.py
- conftest.py
- errors.py
- schemas/area.py
- config.py
- services/profiles.py
- 0010. ROI: one target, measured as rental yield, price growth or total return
- API
- frontend/README.md

## God Nodes (most connected - your core abstractions)
1. `NotImplementedYet` - 59 edges
2. `SerpEngine` - 24 edges
3. `Settings` - 23 edges
4. `InvestorProfileIn` - 21 edges
5. `InvestorProfile` - 20 edges
6. `compilerOptions` - 20 edges
7. `Listing` - 19 edges
8. `compilerOptions` - 17 edges
9. `Base` - 16 edges
10. `Infrastructure` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Added` --references--> `cache_key()`  [INFERRED]
  CHANGELOG.md → backend/app/integrations/serpapi/gateway.py
- `Consequences` --references--> `cache_key()`  [INFERRED]
  docs/decisions/0003-record-replay-and-search-budget.md → backend/app/integrations/serpapi/gateway.py
- `I-02 SerpApi gateway · P0 · 🧱` --references--> `AppError`  [INFERRED]
  CHECKLIST.md → backend/app/core/errors.py
- `F-05 Area intelligence · P0 · 🧱` --references--> `locality_key()`  [INFERRED]
  CHECKLIST.md → backend/app/pipeline/enrichment/area.py
- `Domain schemas` --references--> `QualityFlag`  [INFERRED]
  docs/DATA_MODEL.md → backend/app/schemas/listing.py

## Import Cycles
- None detected.

## Communities (83 total, 36 thin omitted)

### Community 0 - "SerpApi India Hackathon 2026 — Working Brief"
Cohesion: 0.20
Nodes (10): Hard constraints, IP / legal worth knowing, Judges — all SerpApi staff, mostly developer advocates, Landscape — BuiltWithSerpApi gallery (179 public projects, theme counts), Prizes — ₹2,10,000 cash + 120,000 credits competitive, ₹3L+ total value, SerpApi India Hackathon 2026 — Working Brief, Six tracks (pick exactly one; SerpApi may reclassify), Strategic reads (+2 more)

### Community 1 - "Hackathon Submission"
Cohesion: 0.50
Nodes (4): Demo video plan (< 3 min, running locally), Form fields, Hackathon Submission, Pre-submit checks

### Community 3 - "verification.py"
Cohesion: 0.20
Nodes (8): extract(), ExtractedField, ExtractedListing, verify(), ResultKind, Verification, F-03 AI relevance verification · P0 · 🧱, 4 · Verify (`verification.py`, `quality.py`, F-03, F-12)

### Community 4 - "types.ts"
Cohesion: 0.05
Nodes (86): ApiError, ApiErrorBody, apiFetch(), describeError(), useCreateProfile(), useDeleteProfile(), useProfile(), useProfileOptions() (+78 more)

### Community 5 - "routes/portfolio.py"
Cohesion: 0.19
Nodes (11): compare(), list_saved(), save(), unsave(), CompareResult, SavedProperty, SaveRequest, compare() (+3 more)

### Community 6 - "SerpEngine"
Cohesion: 0.05
Nodes (32): Settings, google_maps_reviews(), google_maps_search(), google_news(), google_search(), google_trends(), cache_key(), SerpApiGateway (+24 more)

### Community 7 - "Features"
Cohesion: 0.05
Nodes (39): run_pipeline(), Docs (D-01), F-01 Investor profile · P0 · ✅, F-04 Ranked recommendations · P0 · 🧱, F-06 Competitor analysis (commercial) · P0 · 🧱, F-07 Property detail page · P0 · 🧱, F-08 Saved and compare · P1 · 🧱, F-09 Investment metrics · P0 · 🧱 (+31 more)

### Community 8 - "run.py"
Cohesion: 0.16
Nodes (9): get_recommendations(), get_run(), start_run(), Recommendation, PipelineRun, PipelineStage, RunStatus, get_recommendations() (+1 more)

### Community 9 - "NotImplementedYet"
Cohesion: 0.05
Nodes (22): ProviderMode, NotImplementedYet, LLMProvider, ModelTier, get_llm(), GeminiProvider, RecordingLLM, canonical_url() (+14 more)

### Community 10 - "decisions/README.md"
Cohesion: 0.12
Nodes (13): 0003. Record/replay providers and a hard search budget, Consequences, Context, Decision, 0004. Every investor-facing fact carries source and confidence, Consequences, Context, Decision (+5 more)

### Community 11 - "models.py"
Cohesion: 0.13
Nodes (14): Base, new_id(), utcnow(), AlertRow, AreaIntelRow, CompetitorReportRow, ListingRow, LlmCacheRow (+6 more)

### Community 12 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+13 more)

### Community 13 - "Realty Intel: real estate investor intelligence on SerpApi"
Cohesion: 0.50
Nodes (4): Code rules, Documentation discipline (required), graphify, Realty Intel: real estate investor intelligence on SerpApi

### Community 14 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+10 more)

### Community 15 - "package.json"
Cohesion: 0.14
Nodes (16): name, private, type, version, eslint, @eslint/js, eslint-plugin-react-hooks, globals (+8 more)

### Community 16 - "NNNN. Title"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, NNNN. Title

### Community 17 - "Listing"
Cohesion: 0.22
Nodes (5): compute_metrics(), flag_listing(), AreaIntel, Listing, QualityFlag

### Community 18 - "test_profiles_api.py"
Cohesion: 0.20
Nodes (3): _fields(), test_schema_errors_use_the_shared_422_shape(), test_unknown_locality_and_city_are_rejected()

### Community 19 - "test_profile_schema.py"
Cohesion: 0.08
Nodes (30): create_profile(), delete_profile(), get_profile(), list_profiles(), start_run(), update_profile(), InvestorProfile, InvestorProfileIn (+22 more)

### Community 20 - "devDependencies"
Cohesion: 0.12
Nodes (16): devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, globals, openapi-typescript, tailwindcss, @tailwindcss/vite (+8 more)

### Community 21 - "0008. Code computes scores and money; the LLM extracts and explains"
Cohesion: 0.50
Nodes (4): 0008. Code computes scores and money; the LLM extracts and explains, Consequences, Context, Decision

### Community 22 - "0001. FastAPI + React (Vite, TypeScript) + SQLite"
Cohesion: 0.40
Nodes (4): 0001. FastAPI + React (Vite, TypeScript) + SQLite, Consequences, Context, Decision

### Community 23 - "0006. Enrich per locality, not per property"
Cohesion: 0.40
Nodes (4): 0006. Enrich per locality, not per property, Consequences, Context, Decision

### Community 24 - "Development Guide"
Cohesion: 0.18
Nodes (11): Adding a feature: the usual path, Commands, Configuration, Conventions, Definition of done, Development Guide, Knowledge graph, Known tooling issues (+3 more)

### Community 25 - "Product"
Cohesion: 0.20
Nodes (10): Core value, End-to-end flow, Features, Hackathon framing, One-liner, Problem, Product, Risks and how the design answers them (+2 more)

### Community 26 - "Realty Intel *(working name)*"
Cohesion: 0.25
Nodes (8): AI disclosure, Architecture, Documentation, Quickstart, Realty Intel *(working name)*, Repository layout, What it does, Why

### Community 29 - "Architecture"
Cohesion: 0.25
Nodes (8): Architecture, Configuration, Directory map, Error contract, Key design rules, Layers, Request lifecycle: a pipeline run, System overview

### Community 30 - "S-01 · Data coverage spike (Bengaluru)"
Cohesion: 0.22
Nodes (8): Decisions, Early observations, Enrichment engines, Field availability (share of single-listing hits), Findings per portal, Queries run, S-01 · Data coverage spike (Bengaluru), Setup

### Community 31 - "0002-serpapi-as-the-only-listing-source.md"
Cohesion: 0.40
Nodes (4): 0002. SerpApi is the only listing source; no portal scraping, Consequences, Context, Decision

### Community 32 - "Pipeline"
Cohesion: 0.29
Nodes (7): 1 · Plan (`query_planner.py`, F-02), 2 · Fetch (`discovery.py`, F-02), 3 · Clean (`cleaning.py`, F-02), 5 · Enrich (`enrichment/`, `metrics.py`, F-05, F-06, F-09), 6 · Rank (`ranking.py`, F-04), LLM calls per run, Pipeline

### Community 33 - "dependencies"
Cohesion: 0.29
Nodes (7): dependencies, leaflet, react, react-dom, react-leaflet, react-router, @tanstack/react-query

### Community 34 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, gen:types, lint, preview, test, typecheck

### Community 35 - "[Unreleased]"
Cohesion: 0.50
Nodes (4): Added, Changed, Changelog, [Unreleased]

### Community 36 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 38 - "router.tsx"
Cohesion: 0.14
Nodes (18): useHealth(), AppShell(), BackendStatus(), NAV, Placeholder(), PlaceholderProps, queryClient, AlertsPage() (+10 more)

### Community 39 - "listing.py"
Cohesion: 0.17
Nodes (4): MatchVerdict, QualityFlagKind, InvestmentMetrics, ExtractionMethod

### Community 40 - "0009. SQLite over DuckDB for the app database"
Cohesion: 0.40
Nodes (4): 0009. SQLite over DuckDB for the app database, Consequences, Context, Decision

### Community 41 - "routes/properties.py"
Cohesion: 0.23
Nodes (5): get_area(), get_property(), PropertyDetail, get_area(), get_property_detail()

### Community 42 - "vite.config.ts"
Cohesion: 0.50
Nodes (3): @tailwindcss/vite, vite, @vitejs/plugin-react

### Community 43 - "main.py"
Cohesion: 0.19
Nodes (7): get_settings(), configure_logging(), init_db(), shutdown_scheduler(), start_scheduler(), create_app(), lifespan()

### Community 44 - "views.py"
Cohesion: 0.13
Nodes (9): health(), get_budget(), get_profile_options(), AlertKind, BudgetStatus, HealthStatus, LocalityOption, ProfileOptions (+1 more)

### Community 68 - "router.py"
Cohesion: 0.16
Nodes (3): check_alerts(), list_alerts(), register_exception_handlers()

### Community 69 - "reference/__init__.py"
Cohesion: 0.36
Nodes (3): load_market(), Locality, Market

### Community 73 - "errors.py"
Cohesion: 0.15
Nodes (8): AppError, ReplayMiss, SearchBudgetExceeded, run_alert_check(), Alert, check_alerts(), list_alerts(), I-03 SerpApi record / replay · P0 · 🧱

### Community 74 - "schemas/area.py"
Cohesion: 0.16
Nodes (15): Amenity, AmenityCategory, NewsItem, NewsTopic, PriceTrend, RentalDemand, Sentiment, TrendPoint (+7 more)

### Community 76 - "services/profiles.py"
Cohesion: 0.18
Nodes (13): InvalidInput, NotFound, InvestmentGoal, PropertyType, RiskAppetite, ROIMeasure, Segment, GoalOption (+5 more)

### Community 77 - "0010. ROI: one target, measured as rental yield, price growth or total return"
Cohesion: 0.50
Nodes (4): 0010. ROI: one target, measured as rental yield, price growth or total return, Consequences, Context, Decision

## Knowledge Gaps
- **242 isolated node(s):** `Changed`, `Summary`, `Timeline`, `S-01 Data coverage spike · P0 · 🟨`, `S-02 Gemini extraction accuracy · P0 · ⬜` (+237 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 432 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ApiError` connect `types.ts` to `frontend/README.md`?**
  _High betweenness centrality (0.285) - this node is a cross-community bridge._
- **Why does `Frontend` connect `frontend/README.md` to `types.ts`?**
  _High betweenness centrality (0.285) - this node is a cross-community bridge._
- **Why does `Data Model` connect `Features` to `NotImplementedYet`, `docs/README.md`, `schemas/area.py`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `NotImplementedYet` (e.g. with `GeminiProvider` and `RecordingLLM`) actually correct?**
  _`NotImplementedYet` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `SerpEngine` (e.g. with `google_maps_reviews()` and `google_maps_search()`) actually correct?**
  _`SerpEngine` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `Settings` (e.g. with `get_llm()` and `GeminiProvider`) actually correct?**
  _`Settings` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `InvestorProfileIn` (e.g. with `create_profile()` and `update_profile()`) actually correct?**
  _`InvestorProfileIn` has 5 INFERRED edges - model-reasoned connections that need verification._