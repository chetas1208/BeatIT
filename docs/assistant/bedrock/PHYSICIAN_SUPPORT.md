# Physician copilot support — Wave 5

## E2E behaviors (existing tests)

- Orchestrator model routing: `test_orchestrator_model_routing.py`
- Output safety + numeric claims: same file + `test_safety_validator.py`
- Physician brief tool: Wave 3 physician modules + artifact UI

## Validation gates

1. Model text passes `check_output_safety` before returning to client.
2. Numeric claims cross-checked against `CardiacTwinState` where applicable.
3. `safety_disclaimer` on every assistant API response.

## Bedrock-specific notes

- Physician audience selects **BALANCED** (`MODEL_BALANCED` / Terra).
- Complex reasoning selects **DEEP** (Sol).
- No treatment or emergency directives from LLM path (intake blocking unchanged).
