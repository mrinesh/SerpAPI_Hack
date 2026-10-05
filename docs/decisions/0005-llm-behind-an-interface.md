# 0005. Gemini, behind a provider interface

- **Status:** Superseded by [0012](0012-deepseek-replaces-gemini.md) (provider choice; the interface stands)
- **Date:** 2026-10-03

## Context
The team chose Gemini. LLM calls must also be recordable for replay, and model names change often.

## Decision
The pipeline depends on the `LLMProvider` protocol (`generate_structured`, `generate_text`).
`GeminiProvider` implements it with `google-genai`, passing Pydantic models as `response_schema`.
`RecordingLLM` wraps any provider for record/replay. Two tiers: `GEMINI_MODEL`
(gemini-3.8-flash) for reasoning, `GEMINI_MODEL_LITE` (gemini-3.5-flash-lite) for extraction.
Prompts live in `prompts/<task>.md`.

## Consequences
- Swapping provider or model is a config or one-class change.
- Structured output is validated with the same Pydantic models the API uses.
