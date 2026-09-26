# Wave 2 Handoff — Bedrock provider substrate

## IMPLEMENTED

- `intelligence/bedrock/auth.py`, `chat_completions.py`, `responses.py`
- `BedrockOpenAIProvider` protocol routing (`MODEL_API_PROTOCOL`)
- Extended `ProviderHealth` + `/api/intelligence/status` role fields
- Tests: `test_bedrock_substrate.py`

## VERIFY

```bash
python -m pytest -q python/hearttwin/tests/test_bedrock_substrate.py python/hearttwin/tests/test_api_routes.py::test_intelligence_status_is_safe
```

## NEXT

Wave 3 benchmarks → `MODEL_BENCHMARKS.md`
