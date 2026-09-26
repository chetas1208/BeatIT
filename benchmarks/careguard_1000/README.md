# CareGuard 1,000-Case Benchmark

A reproducible benchmark comparing **Claude Sonnet 4.5** and **Claude Sonnet
4.6** (case-only and evidence-grounded) against the **HeartTwin CareGuard**
medication-safety system, on ~1,000 de-identified composite open-data cases.

> Research benchmark using deidentified, synthetic, or composite open-data
> cases. **Not a clinical-validation study and not for diagnosis or treatment
> decisions.**

## What it answers

1. Does Sonnet 4.6 beat 4.5 given identical case info and prompt?
2. How much does authoritative evidence help each standalone model?
3. Does full CareGuard beat direct standalone model calls?
4. Which CareGuard components create the gain (ablations)?
5. Is CareGuard accurate, reliable, fast, and cheap enough to demo?

See `METHODOLOGY.md` for arms, tracks, and grading; `LIMITATIONS.md`,
`CLAIMS_POLICY.md`, `DATA_LINEAGE.md`, `REPRODUCIBILITY.md`, `BENCHMARK_CARD.md`.

## Layout

```
config/       run/model/metric/grader/subgroup/ablation/report YAML
schemas/      benchmark input/output, reference, trial, grader JSON schemas
prompts/      shared direct-arm + judge prompts
reference/    source-derived reference builder + labels + adjudication queue
runners/      verify_models, build_case_index, estimate_cost, arm runners, resume
graders/      deterministic graders + aggregate
analysis/     bootstrap, paired tests, subgroup/failure/cost/latency, charts, reports
results/      raw/ normalized/ graded/ aggregate/ statistics/ failures/ charts/ reports/
tests/        reference/schema/grader/stats/cost/leakage/reproducibility tests
```

## Quick start

```bash
cd benchmarks/careguard_1000
../../.venv/bin/python runners/verify_models.py        # gate: both models exist
../../.venv/bin/python runners/build_case_index.py     # index 1000 cases
../../.venv/bin/python reference/build_reference_set.py # source-derived labels
../../.venv/bin/python runners/estimate_cost.py        # projected $, no spend
```

- **Free / deterministic path:** `bash run_core_benchmark.sh` — case index,
  reference set, CareGuard Arm E over eligible cases, graders, and a report on
  the deterministic arm. Spends **$0** on models.
- **Full paid path:** `bash run_full_benchmark.sh` — adds the Sonnet 4.5/4.6
  model arms; **requires explicit cost confirmation** and honors
  `config/benchmark.yaml: max_cost_usd`.

Nothing in `data/cases/` is modified. Large raw transcripts and API outputs are
git-ignored (`.gitignore`); code, schemas, configs, methodology, and summarized
results are committed.
