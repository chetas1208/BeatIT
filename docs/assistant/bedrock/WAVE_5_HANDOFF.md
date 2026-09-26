# Wave 5 Handoff — Physician support

## IMPLEMENTED

- `PHYSICIAN_SUPPORT.md` mapping tests and routing (BALANCED/DEEP)
- Bedrock comments in `test_orchestrator_model_routing.py`

## VERIFY

```bash
python -m pytest -q python/hearttwin/tests/test_orchestrator_model_routing.py -k "not TestRealModelRouterIntegration"
```

## NEXT

Wave 6 UI E2E notes in `E2E_RESULTS.md`
