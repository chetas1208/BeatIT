# M6 Shadow Trial performance and reproducibility

**Status:** local synthetic benchmark completed. These are engineering
observations only; they are not hosted capacity, clinical performance, or
patient-data claims.

**Review date:** 2026-09-26

**Scope:** the paired Shadow Trial engine that loads one persisted M5.5
ensemble, applies one bounded scenario to each existing sample, computes paired
scenario-minus-baseline effects, and persists the immutable result.

**Out of scope:** M7 split-heart rendering, M8 missing-piece work, clinical
performance, clinical efficacy, treatment selection, and hosted capacity.

## Existing baseline evidence

The M5.5 benchmark convention is the committed synthetic fixture
`fixtures/hearttwin/manual_baseline.json`, seed `20260926`, one warmup, and
three measured repetitions for each requested count. The checked-in runner is
`scripts/benchmark_ensemble.py`; it measures `run_ensemble` without fixture
loading, request construction, or process startup.

The already recorded M5.5 local baseline in `docs/hackathon/M5_5_PERFORMANCE.md`
is useful for comparison, but it is not an M6 result:

| Requested samples | M5.5 generation median |
|---:|---:|
| 50 | 10.146 ms |
| 100 | 19.791 ms |
| 250 | 51.124 ms |
| 500 | 105.930 ms |
| 1000 | 218.384 ms |

Those values are local synthetic observations, not a target or a hosted
capacity guarantee. M6 must report its own timings because it adds scenario
projection, pair materialization, effect summaries, JSON serialization, and
restart-safe persistence.

## M6 benchmark matrix

Run every row with the same committed synthetic baseline, fixed seed, fixed
scenario definition, and a baseline ensemble generated **once** before the
Shadow Trial timing begins. The baseline must be persisted and loaded for the
trial; generating a new ensemble inside a measured trial would invalidate the
paired design.

| Baseline samples | Shadow core median ms | JSON encode median ms | SQLite save median ms | New-store trial-result load ms | Payload bytes | Valid / invalid |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | 30.510 | 7.616 | 5.971 | 3.505 | 485,611 | 50 / 0 |
| 100 | 60.910 | 15.335 | 11.802 | 7.231 | 966,366 | 100 / 0 |
| 250 | 136.516 | 40.913 | 29.197 | 17.996 | 2,409,066 | 250 / 0 |
| 500 | 375.417 | 79.762 | 58.577 | 37.015 | 4,813,566 | 500 / 0 |
| 1000 | 745.020 | 159.938 | 114.944 | 77.157 | 9,622,571 | 1000 / 0 |

The measurements came from `scripts/benchmark_shadow_trial.py` using
`fixtures/golden/probabilistic/fixed-only.json`, CPython 3.13.12, Linux
6.8.0-139-generic, one warmup, and three measured repetitions. Baseline
generation was excluded from Shadow Trial core timing. Every row reloaded to
an identical payload from a new file-backed SQLite store.

The runner's SQLite save/reload stage is for the Shadow Trial result. It does
not yet separately persist and reload the baseline `EnsembleResponse` before
each measured trial, nor does it run the full subprocess validation matrix.
Those are explicit open reproducibility gates, not capacity claims.

The refreshed run produced these deterministic result identities:

| Baseline samples | Trial ID | Result fingerprint |
|---:|---|---|
| 50 | `shadow-trial-8642d3844c0f` | `8642d3844c0f13f64a69e5bd27390c86f01b6e49d4d6d5745402c6d1ba0a624d` |
| 100 | `shadow-trial-58c7bc6b1f89` | `58c7bc6b1f895c34e97773c00374b2e3019bede88f2a573e3ca622c5b977b67b` |
| 250 | `shadow-trial-130cadebcbc8` | `130cadebcbc8be4b284cdee9572c11a2999638f71d5318afd52f42a4b13d982d` |
| 500 | `shadow-trial-dee0dbb367c6` | `dee0dbb367c681b71ff35708b6971d94b4e11d2f671cba53a198f1fbdbfca5e7` |
| 1000 | `shadow-trial-4014f701c7c8` | `4014f701c7c8db3f510893126f5457eebab68a13683769489a08b6b414597986` |

For each measured stage, report at least minimum, median, mean, and maximum
wall-clock milliseconds over the existing convention of one warmup and three
measured repetitions. A follow-up stability run may use five or more measured
repetitions, but it must identify that change. Also report:

- requested, valid, and invalid pair counts;
- serialized baseline and trial payload sizes in bytes and MiB;
- trial ID and canonical result SHA-256;
- Python version, OS/kernel, CPU description, repository revision, and dirty
  working-tree status;
- whether the database was new or reused, and the database path type (file
  backed, never `:memory:`).

The checked-in M6 benchmark runner is `scripts/benchmark_shadow_trial.py`. It
calls the existing `run_ensemble`, `run_shadow_trial`, and
`SQLiteShadowTrialStore` APIs, uses a fresh file-backed store per sample count,
and prints the raw JSON measurement record. The measurements above are local
engineering evidence only.

### Timing boundaries

Measure the following separately so a fast deterministic core is not confused
with persistence or process overhead:

1. **Baseline generation:** `run_ensemble` once per count, outside the M6 core
   timing, retained as the canonical input for all repetitions.
2. **Baseline persistence:** JSON encoding plus `save`, reported separately
   from the core. Use a fresh database per sample count. **Not separately
   measured by the current runner; open gate.**
3. **Baseline reload:** construct a new store and load the persisted ensemble;
   include JSON decoding, but label process startup separately if a subprocess
   is used. **Not separately measured by the current runner; open gate.**
4. **Shadow core:** `run_shadow_trial` over the already-loaded immutable
   `EnsembleResponse`; do not include fixture load, baseline generation, HTTP,
   or SQLite calls.
5. **Result serialization:** canonical JSON encoding of the returned
   `ShadowTrialResult`.
6. **Trial persistence:** save the serialized result, then load it through a
   newly constructed store and validate it with the result contract.

Use `time.perf_counter_ns()` for in-process stages. If a restart check uses a
child process, report the complete subprocess wall time separately; it is not
an isolated SQLite latency measurement.

## Reproducibility criteria

### Fixed input and provenance

Each run must retain the following exact inputs:

- one M5.5 `EnsembleResponse` persisted before the scenario run;
- the same ensemble ID, origin snapshot ID, seed, physiology version,
  distribution version, prior version, and origin provenance;
- one bounded `ScenarioDefinition`, including parameter IDs, values, units,
  and scenario ID;
- the selected metric IDs and their explicit neutral tolerances;
- M6 engine/physiology versions and the canonical result fingerprint.

The synthetic fixture must remain labeled synthetic. These measurements must
not be described as patient, clinical, efficacy, or treatment evidence.

### No resampling

The following must pass for every sample count:

1. Persist the baseline ensemble before invoking `run_shadow_trial`.
2. Capture each baseline sample ID and parameter vector before the trial.
3. Confirm `requested_pairs == baseline sample count`, including invalid
   samples; invalid pairs are retained rather than silently dropped.
4. Confirm every pair's `sample_id` and `baseline_twin_id` identify the same
   baseline sample, and its baseline state equals the persisted input.
5. Confirm scenario parameters start as a copy of that sample's parameters;
   only explicitly changed bounded parameters differ.
6. Confirm the baseline ensemble's canonical digest is unchanged after the
   trial and that no second ensemble ID, seed, or sample set is created.
7. Add a call-count or spy assertion around any ensemble-generation entry point
   in the harness: the measured shadow stage must invoke zero resampling calls.

The expected scenario ID convention in the current scaffold is
`scenario-{baseline_sample_id}`. A changed convention requires a contract and
test update, not an undocumented benchmark exception.

### Order independence

For each count, run the same persisted ensemble in original, reversed, and at
least two deterministic shuffled sample orders. Compare:

- trial ID and fingerprint;
- ordered pair IDs after canonical engine ordering;
- every baseline/scenario parameter map and delta;
- effect distributions, category counts, and quantiles;
- canonical result SHA-256.

All of these comparisons should be exact for the current deterministic Python
implementation. Wall-clock values are never part of the result digest and are
compared only as measurements.

### Exact versus tolerance-based comparison

Use canonical JSON with sorted keys and compact separators for persisted-result
digests. Require exact equality for IDs, counts, units, provenance, pair maps,
category counts, and serialized values generated by the same environment.

For independently executed environments, retain exact digest comparison as the
first result. If a portability investigation demonstrates floating-point
variation, compare raw metric values with the contract's explicit tolerances
and record the platform difference; do not silently round values before
hashing. The current contract validates summary statistics at approximately
`1e-12` relative/absolute tolerance, while near-zero effect classification uses
the metric-specific tolerances in `NEAR_ZERO_TOLERANCES`.

### Persistence and restart safety

For each count:

1. Save the baseline and trial to a fresh file-backed SQLite database.
2. Construct a new `SQLiteShadowTrialStore` and load both records.
3. In a separate reader process, load and validate the same records when the
   environment permits subprocess testing.
4. Recompute the canonical digests and require equality with the pre-restart
   values.
5. Repeat the same-ID/same-payload save and require idempotent success.
6. Attempt the same ID with a different payload and require rejection; a
   historical trial must not be overwritten.
7. Record file size, payload size, and complete child-process wall time
   separately from the isolated store timings.

The store must remain file-backed and restart-safe. An in-memory result or a
successful same-process lookup alone is insufficient evidence.

## Correctness and failure matrix

The performance run is accepted only if the correctness checks pass first.

| Check | Required result | Measurement status |
|---|---|---|
| 50/100/250/500/1000 requested samples | One pair record per baseline sample | PASS; 0 invalid in synthetic benchmark |
| no-op scenario | Exact zero deltas; baseline input unchanged | Covered by focused test; benchmark matrix NOT RUN |
| reordered baseline samples | Same canonical result and digest | Covered by focused test; benchmark matrix NOT RUN |
| invalid baseline/scenario pair | Pair retained with reason and excluded from effects | Covered by focused test; benchmark matrix NOT RUN |
| no valid pairs | Explicit failed result and empty effect values, never fabricated values | Covered by focused test; benchmark matrix NOT RUN |
| persistence restart | New store/process reproduces canonical digest | PASS for new-store reload; separate-process coverage remains focused |
| bounded scenario | Out-of-range or unsupported values fail clearly | PASS in focused contract/engine tests |
| units | Every delta and distribution has an explicit metric unit | PASS in focused contract/engine tests |

Invalid-pair counts must be reported for every row. A run that reports only
valid pairs, drops rejected samples, or turns missing metrics into zero is a
failed validation regardless of its timing.

## Suggested execution record

Store one machine-readable record beside the eventual benchmark evidence with
this shape:

```json
{
  "benchmark": "m6-shadow-trial",
  "status": "completed-local-synthetic",
  "fixture": "fixtures/hearttwin/manual_baseline.json",
  "seed": 20260926,
  "warmups": 1,
  "repeats": 3,
  "sample_counts": [50, 100, 250, 500, 1000],
  "scenario_id": "<fixed-bounded-scenario>",
  "engine_version": "m6-shadow-trial-v1",
  "measurements": "See the benchmark matrix above and raw JSON from scripts/benchmark_shadow_trial.py",
  "reproducibility": {
    "no_resampling": "pass",
    "order_independence": "pass in focused tests",
    "persistence_restart": "pass for new-store reload"
  },
  "limitations": [
    "Synthetic fixture only",
    "Local wall-clock observations only",
    "No hosted concurrency or capacity claim"
  ]
}
```

Replace `status` and the `not-run` fields only after retaining raw output and
reviewing the acceptance gates above. The evidence must say which stages were
measured and which were skipped.

## Evidence from this review

Inspected and benchmarked on 2026-09-26:

- `docs/hackathon/M5_5_PERFORMANCE.md` for the one-warmup/three-repeat and
  persistence-reporting convention;
- `scripts/benchmark_ensemble.py`, which defines the required sample counts
  `50, 100, 250, 500, 1000` and deterministic seed handling;
- `python/hearttwin/ensemble.py` for the canonical M5.5 evaluator and
  provenance fields;
- `python/hearttwin/shadow_trial_engine.py`,
  `shadow_trial_contracts.py`, and `shadow_trial_identity.py` for current M6
  pairing, ordering, fingerprint, units, and no-resampling behavior;
- `python/hearttwin/storage/shadow_trial_store.py` for file-backed immutable
  SQLite persistence;
- focused M6 tests under `python/hearttwin/tests/test_shadow_trial_*.py`.
- `scripts/benchmark_shadow_trial.py` and the fixed baseline-afterload golden vector.

Existing focused tests cover no-op zero deltas, order-independent replay,
invalid-pair retention, missing-metric failure, pair identity, and store
round-trip/idempotence. They are correctness evidence; the benchmark runner
also measured the matrix above. The benchmark remains synthetic and local.
