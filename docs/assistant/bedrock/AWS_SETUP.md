# AWS Bedrock setup (BeatIT)

## Region and endpoint

- Region: `us-east-1` (workshop default)
- OpenAI-compatible base URL: `https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1`

## Authentication

1. Load workshop IAM session into `.env` (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`).
2. Mint bearer for runtime OpenAI calls:

```bash
python scripts/refresh_bedrock_model_key.py
```

This syncs `MODEL_API_KEY`, `OPENAI_API_KEY`, and `AWS_BEARER_TOKEN_BEDROCK`.

## Required env

| Variable | Purpose |
|----------|---------|
| `INTELLIGENCE_PROVIDER` | `bedrock_openai` |
| `MODEL_BASE_URL` / `OPENAI_BASE_URL` | Bedrock runtime OpenAI base |
| `MODEL_API_KEY` | Bearer token |
| `MODEL_FAST` / `MODEL_BALANCED` / `MODEL_DEEP` | Orchestrator roles |
| `OPENAI_MODEL_*` | Pipeline agent profile IDs |

## Verification

```bash
python scripts/test_bedrock_models.py
python scripts/benchmark_bedrock_roles.py   # optional Wave 3 matrix
curl -s localhost:8000/api/intelligence/status | jq .
```

Do **not** use `GET /models` on `bedrock-runtime` for health; status uses a minimal chat smoke test.

## AgentCore / Guardrails

Evaluated as optional AWS controls; not required for BeatIT demo spine. Deterministic safety validators remain authoritative.
