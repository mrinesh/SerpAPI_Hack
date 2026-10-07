# Architecture Decision Records

Short records of choices someone could reasonably question. Copy [0000-template.md](0000-template.md)
for a new one; never edit an accepted ADR's decision, supersede it with a new one instead.

| # | Decision | Status |
|---|---|---|
| [0001](0001-stack.md) | FastAPI + React (Vite, TypeScript) + SQLite | Accepted |
| [0002](0002-serpapi-as-the-only-listing-source.md) | SerpApi is the only listing source; no portal scraping | Accepted |
| [0003](0003-record-replay-and-search-budget.md) | Record/replay providers and a hard search budget | Accepted |
| [0004](0004-provenance-on-every-field.md) | Every investor-facing fact carries source and confidence | Accepted |
| [0005](0005-llm-behind-an-interface.md) | Gemini, behind a provider interface | Superseded by 0012 |
| [0006](0006-locality-keyed-enrichment.md) | Enrich per locality, not per property | Accepted |
| [0007](0007-single-user-local-app.md) | Single-user local app; auth deferred | Accepted |
| [0008](0008-code-computes-llm-explains.md) | Code computes scores and money; the LLM extracts and explains | Accepted |
| [0009](0009-sqlite-over-duckdb.md) | SQLite over DuckDB; WAL mode, foreign keys on | Accepted |
| [0010](0010-roi-definition.md) | One ROI target: rental yield, price growth or total return; no net yield or cap rate | Accepted |
| [0011](0011-discovery-from-search-snippets.md) | Discovery reads portal search-page snippets and Google Maps projects | Accepted |
| [0012](0012-deepseek-replaces-gemini.md) | DeepSeek V4 Pro replaces Gemini; thinking on for reasoning, off for extraction | Accepted |
| [0013](0013-grounded-verification.md) | Evidence-grounded extraction, hard constraints, per-run verification snapshots | Accepted |
| [0014](0014-area-relative-price-flags.md) | Price flags against a sourced per-locality price level, not a flat rate | Accepted |
| [0015](0015-composite-ranking.md) | Composite ranking in code; grounded AI explanations for the top five | Accepted |
| [0016](0016-area-intelligence-and-score.md) | Area intelligence from five searches; area score is amenity access only | Accepted |
| [0017](0017-investment-metrics-and-roi-score.md) | Rental yield from a quoted area rent; proportional ROI score | Accepted |
| [0018](0018-suggested-target-roi.md) | Suggest the target ROI from the market's sourced typical value | Accepted |
| [0019](0019-visible-failures-validated-cache-withheld-metrics.md) | Visible area failures, validated area cache, withheld metrics (after gscode007's branches) | Accepted |
| [0020](0020-local-news-and-frozen-run-areas.md) | Locality news shown but not scored; frozen per-run area evidence (after gscode007's branch) | Accepted |
| [0021](0021-run-scoped-property-detail.md) | Run-scoped property detail, assembled from stored results | Accepted |
