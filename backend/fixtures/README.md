# Recorded fixtures

Responses recorded in `record` mode and served in `replay` mode, so the app (and the judges)
can run recorded stages with no SerpApi or DeepSeek key and no search credits. S-01 search
fixtures are committed, as are live F-03 DeepSeek recordings for both demo profiles
(`app/reference/demo_profiles.py`): the first 16 residential candidates and all 6 commercial ones.

- `serpapi/<engine>/<cache_key>.json`: `{"engine", "params", "response"}`, where `response` is the
  raw SerpApi JSON. `cache_key` comes from `app/integrations/serpapi/gateway.py::cache_key` and
  must not change once fixtures exist.
- `llm/<task>/<cache_key>.json`: `{key, task, model, tier, response}` containing validated LLM
  output; key includes task, model, tier, schema and prompt.

Fixtures contain public search results only; the gateway strips `api_key` before writing.
Record one search with `SERPAPI_MODE=record uv run python -m app.cli serp google q="..."`, or run
the backend with `make record`. Both spend live searches, unless the response is still in the
database cache; see docs/DEVELOPMENT.md.

`uv run python scripts/record_verification.py --profile residential` (or `commercial`) from
`backend/` records F-03 against existing SerpApi fixtures, spending DeepSeek calls only.
