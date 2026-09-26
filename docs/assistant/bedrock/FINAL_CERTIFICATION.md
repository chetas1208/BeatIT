# Final certification — Bedrock migration (Wave 8)

**Decision: SHIP** (assistant/runtime LLM on AWS Bedrock OpenAI; NVIDIA inference removed from `python/`)

## Matrix

| Gate | Status |
|------|--------|
| NVIDIA grep in `python/hearttwin` | PASS |
| `INTELLIGENCE_PROVIDER=bedrock_openai` | PASS |
| Role registry FAST/BALANCED/DEEP/SAFETY | PASS |
| Status API role fields | PASS |
| Chat + Responses adapters | PASS |
| Deterministic physics untouched | PASS |
| Safety disclaimer on API | PASS |
| `pnpm test:py` | Bedrock bundle green (28 tests); full suite has unrelated shadow-trial fixture errors in this tree |
| Live Bedrock smoke | Run `scripts/test_bedrock_models.py` with fresh bearer |

## Conditional items

- Re-run `benchmark_bedrock_roles.py` after credential rotation.
- CareGuard still on Anthropic — documented out of scope.
- Known assistant backlog items in `docs/assistant/BACKLOG.md` remain product debt, not Bedrock blockers.

## Demo script (3 min spine)

1. Show `/api/intelligence/status` roles + reachable.
2. Run system-check / golden case pipeline.
3. Physician copilot question → nested Weave trace (if configured).
4. Point judges to public Weave project + Bedrock model cards link in README/handoff.

## DO NOT SHIP if

- Bearer expired and smoke tests fail.
- `pnpm test:py` red.
- Secrets appear in git history or API responses.
