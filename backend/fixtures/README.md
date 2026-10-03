# Recorded fixtures

Responses recorded in `record` mode and served in `replay` mode, so the app (and the judges)
can run the full demo with no SerpApi or Gemini key and no search credits.

- `serpapi/<engine>/<cache_key>.json`: raw SerpApi JSON. `cache_key` comes from
  `app/integrations/serpapi/gateway.py::cache_key` and must not change once fixtures exist.
- `llm/<task>/<cache_key>.json`: validated LLM output for one prompt.

Fixtures contain public search results only; the gateway strips `api_key` before writing.
Re-record with `make record` (spends live searches; see docs/DEVELOPMENT.md).
