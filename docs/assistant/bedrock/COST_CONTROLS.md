# Cost controls

- Use **FAST** (Luna) for default copilot turns.
- Reserve **DEEP** (Sol) for Laya-flagged complex reasoning.
- Pipeline agents: lighter `OPENAI_MODEL_*` profiles where stage allows.
- External integration tests gated by `RUN_EXTERNAL_INTEGRATION_TESTS`.
- Benchmark script: 36 calls (12 tasks × 3 roles) — run intentionally, not in CI by default.

Workshop free tier: prefer short `max_completion_tokens` in smoke tests (see `bedrock/health.py` ping).
