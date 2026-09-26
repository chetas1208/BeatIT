# Failure modes — Wave 7

| Scenario | Expected behavior | Test / verify |
|----------|-------------------|---------------|
| Laya disabled | Deterministic / clarification fallback | `test_certification_failure_matrix.py` |
| All models down (`ModelClientError`) | Safe unsupported response + disclaimer | same |
| Invalid model id (live Bedrock) | Orchestrator fallback tree | `test_orchestrator_model_routing.py` (external) |
| Missing bearer | `reachable: false` on status; agents skip LLM | `/api/intelligence/status` |
| Provider disabled | `DisabledIntelligenceProvider` | `test_intelligence_runtime.py` |
| Patient/case isolation | No cross-case state in orchestrator fixtures | existing assistant tests |

Chaos tests do not disable deterministic physics or safety validators.
