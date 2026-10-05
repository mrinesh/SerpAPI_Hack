# Recorded fixtures

Responses recorded in `record` mode and served in `replay` mode, so the app (and the judges)
can run the full demo with no SerpApi or DeepSeek key and no search credits.

- `serpapi/<engine>/<cache_key>.json`: `{"engine", "params", "response"}`, where `response` is the
  raw SerpApi JSON. `cache_key` comes from `app/integrations/serpapi/gateway.py::cache_key` and
  must not change once fixtures exist.
- `llm/<task>/<cache_key>.json`: validated LLM output for one prompt.

Fixtures contain public search results only; the gateway strips `api_key` before writing.
Record one search with `SERPAPI_MODE=record uv run python -m app.cli serp google q="..."`, or run
the backend with `make record`. Both spend live searches, unless the response is still in the
database cache; see docs/DEVELOPMENT.md.
