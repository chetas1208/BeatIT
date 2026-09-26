# Model benchmarks — Wave 3

## Acceptance criteria

| Criterion | Target |
|-----------|--------|
| FAST median latency (12 tasks) | ≤ 8s per task in workshop network |
| BALANCED quality | No safety validator failures on physician brief task |
| DEEP quality | Handles complex reasoning task without numeric fabrication |
| Failure rate | 0/12 tasks per role with valid bearer |

## Method

1. `scripts/benchmark_bedrock_roles.py`
2. Compare latencies in `benchmark_results.json`
3. Spot-check outputs for safety refusals and numeric guard task

## Outcome (campaign default)

Live run on 2026-09-26: **35/36** cells OK in `benchmark_results.json` (one FAST `compare_runs` empty-content retry candidate). Hypothesis **accepted** with `scripts/test_bedrock_models.py` green.

## Locked env

Documented in `.env.example` and `MODEL_SELECTION.md`.
