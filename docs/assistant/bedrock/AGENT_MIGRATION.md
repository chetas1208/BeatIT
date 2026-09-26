# Agent migration — Wave 4

All runtime LLM entry points must use `complete_text` or `chat_completion` (which delegates to `complete_text`).

## Verified paths

| Component | Import |
|-----------|--------|
| Pipeline agents (`intake`, `extraction`, …) | `intelligence.factory.complete_text` |
| `copilot.py` | `complete_text` |
| `tools/image_extract.py` | `complete_text` |
| `assistant/orchestrator.py` | `model_client.chat_completion` → `complete_text` |

## Unauthorized patterns (must be 0 in `python/hearttwin`)

- Direct `AsyncOpenAI` outside `intelligence/openai_provider.py` (CopilotKit tests may patch SDK).
- `nvapi`, `integrate.api.nvidia`, `ModelKeyPool`, `Nemotron` — **0 hits** (enforced in `test_bedrock_substrate.py`).

## CareGuard

Anthropic-backed analysis copilot remains separate until explicitly unified.
