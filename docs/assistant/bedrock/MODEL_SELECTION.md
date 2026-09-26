# Model selection (locked hypothesis — Wave 3)

Benchmark script: `scripts/benchmark_bedrock_roles.py` (12 assistant-shaped tasks × 3 roles).

## Locked routing (2026-09-26)

| Role | Env | Profile ID |
|------|-----|------------|
| FAST | `MODEL_FAST` | `global.openai.gpt-5.6-luna` |
| BALANCED | `MODEL_BALANCED` | `global.openai.gpt-5.6-terra` |
| DEEP | `MODEL_DEEP` | `global.openai.gpt-5.6-sol` |
| SAFETY | `MODEL_SAFETY` | `openai.gpt-oss-safeguard-20b` |

Orchestrator policy:

- DEEP when Laya marks complex reasoning.
- BALANCED when `audience == physician`.
- FAST otherwise.

Pipeline agents continue to use per-stage `OPENAI_MODEL_*` (typically `global.openai.gpt-5.4` / `gpt-5.5` profiles).

## Re-benchmark

When AWS adds models or latency shifts, re-run:

```bash
python scripts/benchmark_bedrock_roles.py
```

Results JSON: `docs/assistant/bedrock/benchmark_results.json` (generated locally; gitignored if empty).

See also `MODEL_BENCHMARKS.md` for acceptance criteria.
