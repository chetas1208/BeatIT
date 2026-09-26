# E2E results — Waves 5–6

## Automated (CI-safe)

| Suite | Scope |
|-------|--------|
| `pnpm test:py` | Full backend including assistant + pipeline |
| `test_orchestrator_model_routing.py` | Mocked generative + safety paths |
| `test_pipeline_actions.py` | CopilotKit pipeline actions |
| `test_certification_failure_matrix.py` | Outage fallbacks |

## Manual / opt-in

| Step | Command |
|------|---------|
| Live Bedrock smoke | `python scripts/test_bedrock_models.py` |
| Role benchmark | `python scripts/benchmark_bedrock_roles.py` |
| Real router integration | `RUN_EXTERNAL_INTEGRATION_TESTS=true pytest …/test_orchestrator_model_routing.py` |
| Frontend copilot | `cd web && pnpm dev` + physician flows |

Twin / compare / evidence UI flows use the same orchestrator seam documented in `ARCHITECTURE.md`.
