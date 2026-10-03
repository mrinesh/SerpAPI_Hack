# Graph Report - SerpAPI_Hack  (2026-10-03)

## Corpus Check
- 133 files · ~28,003 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 8, .example 1, .lock 1)

## Summary
- 833 nodes · 1448 edges · 79 communities (40 shown, 39 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 89 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dcde63b7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SerpApi India Hackathon 2026 — Working Brief
- Realty Intel: real estate investor intelligence on SerpApi
- docs/README.md
- listing.py
- router.tsx
- routes/portfolio.py
- Infrastructure
- Features
- routes/profiles.py
- ModelTier
- decisions/README.md
- main.py
- compilerOptions
- compilerOptions
- package.json
- Realty Intel *(working name)*
- views.py
- services/alerts.py
- devDependencies
- get_budget
- config.py
- errors.py
- Development Guide
- Product
- 0001. FastAPI + React (Vite, TypeScript) + SQLite
- 0006. Enrich per locality, not per property
- run.py
- Architecture
- S-01 · Data coverage spike (Bengaluru)
- 0007. Single-user local app; auth deferred
- Pipeline
- dependencies
- scripts
- verification.py
- schema.d.ts
- 0002. SerpApi is the only listing source; no portal scraping
- 0004-provenance-on-every-field.md
- NotImplementedYet
- Hackathon Submission
- vite.config.ts
- tsconfig.json
- engines
- realty-intel-backend
- types.ts
- compare
- routes/properties.py
- ranking.py
- compute_metrics
- NNNN. Title
- flag_listing
- backend/README.md
- API

## God Nodes (most connected - your core abstractions)
1. `NotImplementedYet` - 61 edges
2. `compilerOptions` - 20 edges
3. `Listing` - 17 edges
4. `compilerOptions` - 17 edges
5. `Base` - 16 edges
6. `Features` - 15 edges
7. `Infrastructure` - 15 edges
8. `GeoPoint` - 13 edges
9. `Sourced` - 13 edges
10. `ModelTier` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Consequences` --references--> `cache_key()`  [INFERRED]
  docs/decisions/0003-record-replay-and-search-budget.md → backend/app/integrations/serpapi/gateway.py
- `F-05 Area intelligence · P0 · 🧱` --references--> `locality_key()`  [INFERRED]
  CHECKLIST.md → backend/app/pipeline/enrichment/area.py
- `4 · Verify (`verification.py`, `quality.py`, F-03, F-12)` --references--> `flag_listing()`  [INFERRED]
  docs/PIPELINE.md → backend/app/pipeline/quality.py
- `Tables` --references--> `rank()`  [INFERRED]
  docs/DATA_MODEL.md → backend/app/pipeline/ranking.py
- `Domain schemas` --references--> `RawSearchHit`  [INFERRED]
  docs/DATA_MODEL.md → backend/app/schemas/listing.py

## Import Cycles
- None detected.

## Communities (79 total, 39 thin omitted)

### Community 0 - "SerpApi India Hackathon 2026 — Working Brief"
Cohesion: 0.20
Nodes (10): Hard constraints, IP / legal worth knowing, Judges — all SerpApi staff, mostly developer advocates, Landscape — BuiltWithSerpApi gallery (179 public projects, theme counts), Prizes — ₹2,10,000 cash + 120,000 credits competitive, ₹3L+ total value, SerpApi India Hackathon 2026 — Working Brief, Six tracks (pick exactly one; SerpApi may reclassify), Strategic reads (+2 more)

### Community 1 - "Realty Intel: real estate investor intelligence on SerpApi"
Cohesion: 0.50
Nodes (4): Code rules, Documentation discipline (required), graphify, Realty Intel: real estate investor intelligence on SerpApi

### Community 3 - "listing.py"
Cohesion: 0.07
Nodes (31): Amenity, AmenityCategory, AreaIntel, NewsItem, NewsTopic, PriceTrend, RentalDemand, Sentiment (+23 more)

### Community 4 - "router.tsx"
Cohesion: 0.09
Nodes (25): Frontend, ApiError, ApiErrorBody, apiFetch(), useHealth(), HealthStatus, AppShell(), BackendStatus() (+17 more)

### Community 5 - "routes/portfolio.py"
Cohesion: 0.22
Nodes (7): CompareResult, SavedProperty, SaveRequest, compare(), list_saved(), save(), unsave()

### Community 6 - "Infrastructure"
Cohesion: 0.05
Nodes (29): AppError, NotFound, ReplayMiss, SearchBudgetExceeded, cache_key(), SerpResponse, run_pipeline(), Recorded fixtures (+21 more)

### Community 7 - "Features"
Cohesion: 0.07
Nodes (28): canonical_url(), locality_key(), Docs (D-01), F-01 Investor profile · P0 · 🧱, F-04 Ranked recommendations · P0 · 🧱, F-05 Area intelligence · P0 · 🧱, F-06 Competitor analysis (commercial) · P0 · 🧱, F-07 Property detail page · P0 · 🧱 (+20 more)

### Community 8 - "routes/profiles.py"
Cohesion: 0.11
Nodes (14): create_profile(), get_profile(), list_profiles(), start_run(), update_profile(), InvestorProfile, InvestorProfileIn, create_profile() (+6 more)

### Community 9 - "ModelTier"
Cohesion: 0.11
Nodes (6): LLMProvider, ModelTier, get_llm(), GeminiProvider, RecordingLLM, Decision

### Community 10 - "decisions/README.md"
Cohesion: 0.12
Nodes (12): 0003. Record/replay providers and a hard search budget, Consequences, Context, Decision, 0005. Gemini, behind a provider interface, Consequences, Context, 0008. Code computes scores and money; the LLM extracts and explains (+4 more)

### Community 11 - "main.py"
Cohesion: 0.05
Nodes (25): get_settings(), register_exception_handlers(), configure_logging(), Base, new_id(), utcnow(), AlertRow, AreaIntelRow (+17 more)

### Community 12 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+13 more)

### Community 14 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+10 more)

### Community 15 - "package.json"
Cohesion: 0.14
Nodes (16): name, private, type, version, eslint, @eslint/js, eslint-plugin-react-hooks, globals (+8 more)

### Community 17 - "Realty Intel *(working name)*"
Cohesion: 0.09
Nodes (21): google_maps_reviews(), google_maps_search(), google_news(), google_search(), google_trends(), Cost model *(estimate; confirmed in S-03)*, Data handling, Engines and their roles (+13 more)

### Community 18 - "views.py"
Cohesion: 0.14
Nodes (5): health(), ProviderMode, AlertKind, BudgetStatus, HealthStatus

### Community 19 - "services/alerts.py"
Cohesion: 0.20
Nodes (5): check_alerts(), list_alerts(), Alert, check_alerts(), list_alerts()

### Community 20 - "devDependencies"
Cohesion: 0.13
Nodes (15): devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, globals, openapi-typescript, tailwindcss, @tailwindcss/vite (+7 more)

### Community 23 - "errors.py"
Cohesion: 0.17
Nodes (5): fetch_hits(), plan_queries(), PlannedQuery, RawSearchHit, F-02 Property discovery · P0 · 🧱

### Community 24 - "Development Guide"
Cohesion: 0.20
Nodes (10): Adding a feature: the usual path, Commands, Configuration, Conventions, Definition of done, Development Guide, Knowledge graph, Prerequisites (+2 more)

### Community 25 - "Product"
Cohesion: 0.20
Nodes (10): Core value, End-to-end flow, Features, Hackathon framing, One-liner, Problem, Product, Risks and how the design answers them (+2 more)

### Community 26 - "0001. FastAPI + React (Vite, TypeScript) + SQLite"
Cohesion: 0.40
Nodes (4): 0001. FastAPI + React (Vite, TypeScript) + SQLite, Consequences, Context, Decision

### Community 27 - "0006. Enrich per locality, not per property"
Cohesion: 0.40
Nodes (4): 0006. Enrich per locality, not per property, Consequences, Context, Decision

### Community 28 - "run.py"
Cohesion: 0.10
Nodes (10): get_recommendations(), get_run(), start_run(), Recommendation, PipelineRun, PipelineStage, RunStatus, StageEvent (+2 more)

### Community 29 - "Architecture"
Cohesion: 0.25
Nodes (8): Architecture, Configuration, Directory map, Error contract, Key design rules, Layers, Request lifecycle: a pipeline run, System overview

### Community 30 - "S-01 · Data coverage spike (Bengaluru)"
Cohesion: 0.25
Nodes (7): Decisions, Enrichment engines, Field availability (share of single-listing hits), Findings per portal, Queries run, S-01 · Data coverage spike (Bengaluru), Setup

### Community 31 - "0007. Single-user local app; auth deferred"
Cohesion: 0.40
Nodes (4): 0007. Single-user local app; auth deferred, Consequences, Context, Decision

### Community 32 - "Pipeline"
Cohesion: 0.29
Nodes (7): 1 · Plan (`query_planner.py`, F-02), 2 · Fetch (`discovery.py`, F-02), 3 · Clean (`cleaning.py`, F-02), 5 · Enrich (`enrichment/`, `metrics.py`, F-05, F-06, F-09), 6 · Rank (`ranking.py`, F-04), LLM calls per run, Pipeline

### Community 33 - "dependencies"
Cohesion: 0.29
Nodes (7): dependencies, leaflet, react, react-dom, react-leaflet, react-router, @tanstack/react-query

### Community 34 - "scripts"
Cohesion: 0.29
Nodes (7): scripts, build, dev, gen:types, lint, preview, typecheck

### Community 35 - "verification.py"
Cohesion: 0.13
Nodes (9): PipelineContext, get_area_intel(), get_competitor_report(), extract(), ExtractedField, ExtractedListing, verify(), F-03 AI relevance verification · P0 · 🧱 (+1 more)

### Community 36 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 38 - "0002. SerpApi is the only listing source; no portal scraping"
Cohesion: 0.50
Nodes (4): 0002. SerpApi is the only listing source; no portal scraping, Consequences, Context, Decision

### Community 39 - "0004-provenance-on-every-field.md"
Cohesion: 0.40
Nodes (4): 0004. Every investor-facing fact carries source and confidence, Consequences, Context, Decision

### Community 40 - "NotImplementedYet"
Cohesion: 0.15
Nodes (7): NotImplementedYet, detect_portal(), normalize_hits(), parse_area_sqft(), parse_price_inr(), get_area(), get_property_detail()

### Community 41 - "Hackathon Submission"
Cohesion: 0.50
Nodes (4): Demo video plan (< 3 min, running locally), Form fields, Hackathon Submission, Pre-submit checks

### Community 42 - "vite.config.ts"
Cohesion: 0.50
Nodes (3): @tailwindcss/vite, vite, @vitejs/plugin-react

### Community 70 - "types.ts"
Cohesion: 0.11
Nodes (17): Alert, AreaIntel, BudgetStatus, CompareResult, CompetitorReport, InvestmentMetrics, InvestorProfile, InvestorProfileIn (+9 more)

### Community 71 - "compare"
Cohesion: 0.16
Nodes (4): compare(), list_saved(), save(), unsave()

### Community 75 - "NNNN. Title"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, NNNN. Title

## Knowledge Gaps
- **226 isolated node(s):** `Backend`, `components`, `$defs`, `operations`, `paths` (+221 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 428 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NotImplementedYet` connect `NotImplementedYet` to `verification.py`, `listing.py`, `routes/portfolio.py`, `Infrastructure`, `Features`, `routes/profiles.py`, `ModelTier`, `compute_metrics`, `ranking.py`, `flag_listing`, `views.py`, `services/alerts.py`, `get_budget`, `config.py`, `errors.py`, `run.py`?**
  _High betweenness centrality (0.240) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Listing` (e.g. with `GeoPoint` and `PropertyType`) actually correct?**
  _`Listing` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Backend`, `components`, `$defs` to the rest of the system?**
  _226 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `listing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06832298136645963 - nodes in this community are weakly interconnected._
- **Should `router.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.09080841638981174 - nodes in this community are weakly interconnected._
- **Should `Infrastructure` be split into smaller, more focused modules?**
  _Cohesion score 0.05426356589147287 - nodes in this community are weakly interconnected._
- **Should `Features` be split into smaller, more focused modules?**
  _Cohesion score 0.06666666666666667 - nodes in this community are weakly interconnected._