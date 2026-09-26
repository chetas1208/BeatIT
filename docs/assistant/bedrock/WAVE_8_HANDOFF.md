# Wave 8 Handoff — Certification

## IMPLEMENTED

- `FINAL_CERTIFICATION.md` — **SHIP** conditional on test suite + live smoke
- Full doc tree under `docs/assistant/bedrock/`

## VERIFY

```bash
pnpm test:py
python scripts/test_bedrock_models.py
```

## Campaign complete

NVIDIA inference removed; Bedrock OpenAI is the assistant/runtime provider.
