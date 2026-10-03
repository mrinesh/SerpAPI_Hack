# Backend

FastAPI service: SerpApi discovery, Gemini verification, area and competitor enrichment, ranking.

```bash
uv sync                                          # install
uv run uvicorn app.main:app --reload --port 8000 # run (or `make backend` from the repo root)
uv run pytest                                    # test
uv run ruff check . && uv run ruff format .      # lint / format
```

| Path | What |
|---|---|
| `app/main.py` | App factory, lifespan (DB init, scheduler) |
| `app/config.py` | All settings and provider modes |
| `app/api/` | Routes; thin, call services |
| `app/services/` | Use cases behind each route |
| `app/pipeline/` | One module per stage: plan, fetch, clean, verify, enrich, rank |
| `app/integrations/serpapi/` | The only code that calls SerpApi (cache, budget, record/replay) |
| `app/integrations/llm/` | Gemini provider, record/replay, prompts |
| `app/schemas/` | Pydantic domain models, the shared contract |
| `app/db/` | SQLAlchemy tables and session |
| `fixtures/` | Recorded SerpApi and LLM responses (committed) |
| `openapi.json` | Exported API schema; source for frontend types (`make types`) |

Full docs: [../docs/README.md](../docs/README.md).
