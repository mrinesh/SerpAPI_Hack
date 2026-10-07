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

F-09 is recorded for both demo profiles: four new Google searches (rent/growth for each
locality/type) and three DeepSeek selections (one eligible rent, two growth selections).
Whitefield rental evidence remains unavailable; Koramangala annual office growth remains
unavailable. These gaps are intentionally preserved, rather than fabricated for replay.
From `backend/`, `uv run python scripts/record_investment_metrics.py --profile both` records
missing responses in a temporary DB while reusing all existing provider fixtures.

Search-driven area research adds four real `google_trends` fixtures (broad and rental interest
for Whitefield and Koramangala, `IN-KA`, `today 5-y`) and two real `review_development` DeepSeek
responses. Each report retains 104 complete public weeks; falling rental histories receive no
priority rank. App histories are collected from real run starts, never seeded as provider data.
`uv run python scripts/record_search_growth.py --profile both` records these in an isolated DB.
