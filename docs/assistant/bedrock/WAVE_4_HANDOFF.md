# Wave 4 Handoff — Agent migration

## IMPLEMENTED

- Inventory + grep gate documented in `AGENT_MIGRATION.md`
- `test_bedrock_substrate.py::test_python_tree_has_no_nvidia_inference`

## VERIFY

```bash
python -m pytest -q python/hearttwin/tests/test_bedrock_substrate.py::test_python_tree_has_no_nvidia_inference
```

## NEXT

Wave 5 physician E2E documentation + existing orchestrator tests
