# Realty Intel: real estate investor intelligence on SerpApi

SerpApi India Hackathon 2026 entry (deadline **Oct 12, 2026, 23:59 IST**, extended from Oct 10; track Commerce &
Market Intelligence; demo market Bengaluru). Constraints: [HACKATHON_BRIEF.md](HACKATHON_BRIEF.md).
Product: [docs/PRODUCT.md](docs/PRODUCT.md). Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Stack: FastAPI (uv) backend in `backend/`, React + Vite + TypeScript frontend in `frontend/`,
SQLite, official `serpapi` SDK, DeepSeek V4 Pro via the `openai` SDK (ADR 0012).

## Documentation discipline (required)

Keep docs and the tracker current as work happens, not at the end:
- **[CHECKLIST.md](CHECKLIST.md)** is the source of truth for status. When starting an item mark
  it 🟨; when finishing, tick its boxes and set ✅, in the same change as the code.
- Walk the **definition of done** in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#definition-of-done)
  before calling anything done: tests, lint, CHECKLIST, affected docs (API.md status column,
  PIPELINE.md, DATA_MODEL.md, SERPAPI_USAGE.md), and a CHANGELOG line.
- New choices someone could question get an ADR in `docs/decisions/`.
- Spike findings go in `docs/spikes/`.

## Code rules

- Layers point one way: `api → services → pipeline → integrations`.
- Only `backend/app/integrations/serpapi/gateway.py` imports `serpapi`; only
  `backend/app/integrations/llm/` imports `openai`.
- Investor-facing facts are `Sourced[T]`. Scores and money are computed in code; the LLM only
  extracts and explains (ADR 0008).
- Unbuilt code raises `NotImplementedYet("<CHECKLIST ID>", "...")`; grep the ID to find stubs.
- Never spend live SerpApi searches casually: 250/month free tier. Default modes are `replay`;
  use `record` deliberately and commit the fixtures. One-off searches go through the gateway:
  `uv run python -m app.cli serp <engine> q="..."` (never call `serpapi` directly).
- After changing a Pydantic schema run `make types`. Never hand-write frontend response types.
- `make lint` and `make test` must pass.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
