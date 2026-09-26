# Reproducibility

## Environment

- Python 3.14, repo `.venv`.
- Packages: `anthropic`, `pandas`, `pyarrow`, `jsonschema`, `scipy`, `numpy`,
  `matplotlib`, `reportlab`, `markdown`, `pyyaml`.
- `ANTHROPIC_API_KEY` in the repo `.env` (never committed).

## Pinned, verified models

`claude-sonnet-4-5-20250929` and `claude-sonnet-4-6`, both confirmed against the
Models API by `runners/verify_models.py` before any arm runs. The verifier
fails closed if either is unavailable or resolves to a different id.

## Deterministic layers (fully reproducible)

- `runners/build_case_index.py` → `results/case_index.{parquet,csv}`
- `reference/build_reference_set.py` → `reference/reference_labels.ndjson`
- Canonical + evidence packet builders (`runners/*packet*`, in
  `runners/run_direct_baseline.py` helpers)
- Arm E CareGuard engine (`runners/run_careguard.py`) — offline, deterministic
- All graders and analysis

Re-running these on the same case files reproduces byte-identical outputs.

## Non-deterministic layer (model arms)

Model responses vary run-to-run (no API seed). Reproducibility is provided by:
pinned model ids, fixed request shape, fixed input packets, fixed grader code,
and the raw transcript store (`results/raw/`, git-ignored). Reliability is
quantified by `runners/run_repeated_trials.py` (3 trials on a 200-case
stratified subset).

## Ordering to reproduce a full run

```
.venv/bin/python runners/verify_models.py
.venv/bin/python runners/build_case_index.py
.venv/bin/python reference/build_reference_set.py
.venv/bin/python runners/estimate_cost.py           # prints projected $ and stops
# review cost, then (paid):
.venv/bin/python run_benchmark.py --arms all --confirm-cost
.venv/bin/python run_benchmark.py --grade --analyze --report
```

`run_core_benchmark.sh` runs the free/deterministic path end-to-end (case
index, reference, Arm E, graders on Arm E). `run_full_benchmark.sh` adds the
paid model arms and requires an explicit cost confirmation.

## Cost governance

`config/benchmark.yaml: max_cost_usd` caps spend; `require_cost_confirmation`
forces an explicit `--confirm-cost` (or `BENCHMARK_CONFIRM_COST=1`). Runners
abort before exceeding the cap and checkpoint after every trial so a run can be
resumed (`runners/resume_failed_trials.py`).
