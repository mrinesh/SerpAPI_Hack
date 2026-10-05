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
