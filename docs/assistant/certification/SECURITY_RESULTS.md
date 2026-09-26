# Security Results (Certification Wave D4–D5)

## Secrets

- NVIDIA keys: `MODEL_API_KEY_1/2/3` server-side only; tests use fake literals.
- No `NEXT_PUBLIC_*` model keys in web bundle (grep clean for assistant path).

## Prompt / tool injection

- Input rail: `classify_request_safety` + intake rules.
- Tool args: schema validation via Pydantic on `AssistantRequest`.
- Adversarial gaps: 6 xfail cases documented; optional NVIDIA safety model evaluated, not enabled by default.

## Logging

- Orchestrator trace stores operational metadata, not raw prompts in API response.
- Do not log `.env` contents (operator responsibility).

## CareGuard

Separate Anthropic path — out of unified rail scope; feature-flagged.
