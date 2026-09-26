# M6 Shadow Trial benchmark and reproducibility review

**Review date:** 2026-09-26  
**Scope:** `scripts/benchmark_shadow_trial.py` and
`docs/hackathon/M6_PERFORMANCE.md`  
**Implementation changes:** none

## Verdict

**Conditional pass for the deterministic paired engine; fail for the benchmark
report's full reproducibility envelope.**

The engine produced exact, order-independent paired results for all requested
sample counts, retained one pair per baseline sample, did not mutate the input,
and did not call the ensemble generator during the shadow stage. The file-backed
store also survived a separate reader process in this review.

The checked-in benchmark runner does not, however, execute several gates that
`M6_PERFORMANCE.md` requires: it does not persist/reload the baseline ensemble,
does not perform a child-process restart check, does not validate the reloaded
trial with `ShadowTrialResult`, and does not assert immutable replay/conflict
behavior. Its timing output is therefore a local stage measurement, not proof
of the complete persisted-baseline/restart envelope.

## Commands and environment

Benchmark rerun:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  python scripts/benchmark_shadow_trial.py
```

Observed environment:

```text
Python 3.13.12
Linux-6.8.0-139-generic-x86_64-with-glibc2.39
fixture: fixtures/golden/probabilistic/fixed-only.json
counts: 50, 100, 250, 500, 1000
```

Focused verification:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev pytest -q \
  python/hearttwin/tests/test_shadow_trial_reproducibility.py \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_shadow_trial_store.py \
  python/hearttwin/tests/test_shadow_trial_golden.py
21 passed in 0.47s
```

The repository was already dirty with unrelated and M6 changes; this review
does not claim a clean revision or commit-level reproducibility.

## Rerun measurements

The runner uses one unreported shadow warmup and three measured repetitions.
The values below are calculated from the raw arrays emitted by that invocation.
`sqlite_reload_ms` is the single same-process `get()` measurement emitted by
the runner; it is not a subprocess restart time.

| Requested pairs | Shadow core min / median / mean / max ms | JSON encode min / median / mean / max ms | SQLite save min / median / mean / max ms | Reload ms | Payload bytes | Valid / invalid |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | 43.184 / 47.890 / 46.483 / 48.375 | 7.848 / 8.152 / 8.221 / 8.664 | 6.362 / 10.881 / 18.875 / 39.381 | 8.746 | 485,611 | 50 / 0 |
| 100 | 50.949 / 58.153 / 59.234 / 68.599 | 15.182 / 15.291 / 15.320 / 15.486 | 11.553 / 11.855 / 17.928 / 30.377 | 7.305 | 966,366 | 100 / 0 |
| 250 | 131.267 / 132.305 / 137.846 / 149.965 | 37.498 / 41.088 / 52.209 / 78.040 | 29.772 / 37.695 / 52.989 / 91.500 | 18.445 | 2,409,066 | 250 / 0 |
| 500 | 318.773 / 420.558 / 389.345 / 428.705 | 82.859 / 84.930 / 95.131 / 117.603 | 59.033 / 61.063 / 84.596 / 133.693 | 37.512 | 4,813,566 | 500 / 0 |
| 1000 | 705.561 / 751.856 / 752.857 / 801.155 | 163.144 / 165.760 / 177.741 / 204.319 | 115.612 / 116.798 / 156.109 / 235.916 | 78.609 | 9,622,571 | 1000 / 0 |

Trial IDs and fingerprints matched the values already listed in
`M6_PERFORMANCE.md`. The payload sizes and valid/invalid counts also matched.
The timing table did not: for example, the checked-in 1000-pair shadow median
is `745.020 ms`, while this rerun measured `751.856 ms`; the 50-pair values
were `30.510 ms` versus `47.890 ms`. These are normal local wall-clock
observations, but the report should identify the older table as a prior run or
retain raw run records rather than call it a refreshed result without a run
artifact.

## Reproducibility checks performed in this review

An independent read-only harness built the same fixed baseline for each count,
then compared the original sample order, reversed order, and two deterministic
shuffles. It also captured a canonical SHA-256 digest of the baseline before
and after the trial.

| Check | 50 | 100 | 250 | 500 | 1000 |
|---|---:|---:|---:|---:|---:|
| Exact result equality across reverse + 2 shuffles | PASS | PASS | PASS | PASS | PASS |
| Requested pairs equal pair records and count | PASS | PASS | PASS | PASS | PASS |
| `sample_id == baseline_twin_id`; scenario ID ends in sample ID | PASS | PASS | PASS | PASS | PASS |
| Baseline digest unchanged | PASS | PASS | PASS | PASS | PASS |

The same harness replaced `python.hearttwin.ensemble.run_ensemble` with a
failing spy after baseline generation. `run_shadow_trial` completed, providing
direct evidence that the measured shadow stage made zero calls to the ensemble
generator. This is an audit harness result, not a check currently embedded in
`scripts/benchmark_shadow_trial.py`.

Persistence checks in a separate temporary file-backed SQLite database passed:

- same-ID/same-payload replay was accepted;
- same-ID/different-payload write was rejected;
- a separate Python process loaded the record exactly;
- `ShadowTrialResult.model_validate()` reproduced the persisted payload.

These checks strengthen the store result, but they are not all performed by the
checked-in benchmark script.

## Harness audit

The benchmark script correctly does the following:

- generates one baseline per sample count and reuses that in-memory object for
  the warmup and three measured shadow calls;
- separates shadow execution, JSON encoding, SQLite save, and SQLite load
  timings;
- uses a fresh file-backed temporary store per count;
- reports requested, valid, invalid, payload bytes, IDs, fingerprints, and
  exact dictionary equality after `get()`.

The following gaps prevent a full reproducibility PASS against the report's own
acceptance criteria:

1. **Baseline persistence is absent.** Lines 32 and 39–47 generate and pass an
   in-memory `baseline`; lines 44–53 save only the trial payload. The report
   requires the baseline to be persisted before the shadow run and reloaded for
   the measured trial.
2. **Restart is same-process only.** `SQLiteShadowTrialStore` is reconstructed
   only inside the benchmark process. There is no child-process load, process
   wall time, or database file-size record.
3. **Reload contract validation is absent.** `reload_matches` compares a dict
   returned by `store.get()` with the original dict. It does not call
   `ShadowTrialResult.model_validate()` or recompute the canonical fingerprint.
4. **Immutable-write gates are absent.** The three save calls are repeated
   identical writes; the runner does not attempt a conflicting payload and does
   not assert that the first record remains unchanged.
5. **Input/result identity is not asserted per repetition.** Each measured
   result is timed and discarded except for the final trial metadata. The
   runner does not compare each result payload to the warmup result or assert
   that all three IDs/fingerprints are identical.
6. **Reported payload scope is incomplete.** `payload_bytes` measures only the
   trial JSON, while the report's evidence requirements ask for serialized
   baseline and trial sizes in bytes and MiB.
7. **No raw evidence artifact is retained by the repository.** The command
   prints JSON to stdout, but the checked-in report does not link to a captured
   machine-readable run, host CPU description, or repository state.

## Review conclusion

The numerical and identity behavior is reproducible within this environment,
and the local result-store behavior is supported by both focused tests and the
separate-process audit above. The current performance numbers should be treated
as a local synthetic envelope only, not as hosted capacity or clinical
evidence.

For M6 to claim the full benchmark/reproducibility gate, the next benchmark
revision should persist and reload the baseline before timing the shadow stage,
validate the reloaded result contract and digest, exercise a child-process
reader, record baseline/trial sizes and raw JSON, and include explicit
same-ID-conflict and per-repetition identity assertions. Those are review
recommendations; no implementation files were changed in this review.
