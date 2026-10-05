# 0012. DeepSeek replaces Gemini as the LLM provider

- **Status:** Accepted
- **Date:** 2026-10-05

## Context
The team has a DeepSeek API key and chose DeepSeek V4 Pro for the product's LLM work. The
Gemini provider from ADR 0005 was still a stub (I-06), so no prompt or fixture depended on it.
The `LLMProvider` interface from ADR 0005 stays as it is; only the implementation changes.

## Decision
`DeepSeekProvider` implements `LLMProvider` and replaces `GeminiProvider`. This supersedes the
provider choice in ADR 0005 and the `google-genai` line in ADR 0001.

- **SDK:** the `openai` package pointed at `DEEPSEEK_BASE_URL` (`https://api.deepseek.com`).
  DeepSeek's API is OpenAI-compatible and its docs use this SDK. Only `integrations/llm/`
  imports `openai`.
- **Model and tiers:** both tiers default to `deepseek-v4-pro`. The tiers differ in thinking
  mode, not in model: `REASONING` (scoring, explanations) sends `thinking: enabled`, and `LITE`
  (bulk extraction) sends `thinking: disabled`. Thinking off was about 5× cheaper in output tokens
  and 1.4 s against 7 s on the same extraction, with the same fields. `DEEPSEEK_MODEL_LITE` can
  be pointed at `deepseek-flash` if extraction volume makes cost matter.
- **Structured output:** JSON output mode (`response_format={"type": "json_object"}`). DeepSeek
  takes no schema parameter, so the Pydantic model's JSON schema goes in the system prompt, which
  also satisfies the API's rule that the prompt contain the word "json". The reply is validated
  with the same model. An empty or invalid reply is retried once with the error sent back.
- **Limits:** `DEEPSEEK_MAX_TOKENS` (16384) counts thinking tokens too, so it must leave room for
  the JSON. `DEEPSEEK_TIMEOUT_S` is 120 because thinking replies take several seconds.

## Consequences
- Structured output is guided by the prompt rather than enforced by the API, so validation plus
  one retry is the only guarantee. Watch the retry rate in S-02.
- deepseek-v4-pro has no image input. If a feature needs vision, it needs `deepseek-flash` or
  another provider.
- Record/replay (I-07) is unchanged: replay mode still needs no LLM key.
