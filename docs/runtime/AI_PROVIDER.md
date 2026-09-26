# BeatIT AI provider runtime

BeatIT's cardiac engine is provider-independent. EF, SV, CO, MAP, QTc, PV
loops, AHA mappings, causal propagation, cardiac-clock state, and longitudinal
numeric snapshots are computed by deterministic BeatIT code. External models
only extract untrusted candidates or produce grounded educational language.

## Configuration

The default runtime is an OpenAI-compatible endpoint selected by:

```bash
INTELLIGENCE_PROVIDER=generic
MODEL_ENABLED=true
MODEL_API_PROTOCOL=openai-compatible
MODEL_API_KEY=...
MODEL_BASE_URL=https://endpoint.example/v1
MODEL_NAME=...
MODEL_TIMEOUT_SECONDS=45
MODEL_MAX_RETRIES=2
```

The generic adapter never assumes `api.openai.com`. A real optional
`OpenAIProvider` is available with `INTELLIGENCE_PROVIDER=openai` and
`OPENAI_ENABLED=true`; it remains disabled by default. `disabled` mode is
failure-safe and is used automatically when configuration is incomplete.

All authenticated calls are server-side. No `NEXT_PUBLIC_*` model or AWS
secret is supported.

`GET /api/intelligence/status` (also `/api/v1/intelligence/status`) returns
only provider, protocol, enabled, reachability, and model-configured flags.
