# M8 Missing Piece performance record

**Status:** benchmark procedure documented; a narrow local probe was run on
2026-09-26 and is recorded below. It is not a hosted-capacity claim.

**Scope:** the deterministic `run_missing_piece` engine over an already
materialized M5.5 `EnsembleResponse`. The engine uses persisted sample
parameters and projection bases, bounded finite perturbations, empirical
parameter spread, uncertainty-impact heuristics, evidence ranking, and
completeness metadata.

**Out of scope:** clinical performance, hosted capacity, concurrent-user
capacity, browser frame rate, GPU performance, model latency, and any claim of
expected information gain or measurement-error reduction.

## Deterministic work and scaling

Let `N` be the number of accepted or rejected ensemble samples and `P` the
number of bounded model parameters. The current evaluator has `P = 5`:
`heart_rate_bpm`, `preload_index`, `afterload_index`, `contractility_index`,
and `systemic_vascular_resistance_index`.

For each valid sample and each parameter, M8 evaluates the persisted baseline
and one or two bounded perturbations. A central difference therefore performs
one baseline evaluation plus two perturbed evaluations per parameter; a
one-sided difference performs one baseline plus one perturbed evaluation for
that parameter. The baseline is recomputed from the persisted projection base
and is not taken from a possibly stale stored output.

The resulting asymptotic costs are:

| Stage | Time | Additional space | Notes |
|---|---:|---:|---|
| Per-sample sensitivity | `O(P)` canonical evaluations | `O(P)` records | Bounded finite differences; no resampling |
| All sample sensitivities | `O(NP)` | `O(NP)` transient records | Invalid/unavailable samples retain explicit reasons |
| Per-parameter median aggregation | `O(N log N)` total for fixed `P` | `O(N)` sorting workspace | Deterministic sorted sample order and medians |
| Parameter uncertainty | `O(NP)` | `O(N)` values per parameter | Descriptive q05/q95 spread over declared bounds |
| Impact and evidence ranking | `O(P log P)` | `O(P)` | Fixed-size target-specific ranking |

With the current five-parameter model, end-to-end engine work is effectively
linear in `N`, with a sorting term for the per-parameter medians. The output is
compact, but the implementation temporarily retains per-sample sensitivity
records while aggregating them. Large `N` therefore increases both evaluator
time and Python memory use.

The engine is deterministic for the same persisted ensemble, target metric,
engine version, and evidence-type list. It does not sample, mutate the input
ensemble, or run an external model. Timing must exclude ensemble generation
when measuring M8 itself; generation is the M5.5 workload and should be
reported separately using the existing `scripts/benchmark_ensemble.py`
convention.

## Focused benchmark command

The following command follows the existing M5.5 convention: one warmup, three
measured repetitions, committed synthetic input, fixed seed, and separate
sample counts. It generates the baseline once per row, then measures only
`run_missing_piece` on that baseline. The reported values are produced by the
invocation and are not pre-recorded claims.

```bash
PYTHONPATH=. uv run --project . --extra dev python - <<'PY'
import json
import platform
import time
from statistics import mean, median

from scripts.benchmark_ensemble import _build_request, _load_synthetic_state
from python.hearttwin.ensemble import run_ensemble
from python.hearttwin.missing_piece.engine import run_missing_piece

state = _load_synthetic_state()
for sample_count in (50, 100, 250, 500, 1000):
    baseline = run_ensemble(_build_request(state, sample_count, 20260926))
    for _ in range(1):
        run_missing_piece(baseline, "stroke_volume_ml")
    durations_ms = []
    for _ in range(3):
        started = time.perf_counter_ns()
        result = run_missing_piece(baseline, "stroke_volume_ml")
        durations_ms.append((time.perf_counter_ns() - started) / 1_000_000)
    print(json.dumps({
        "sample_count": sample_count,
        "valid_samples": sum(1 for sample in baseline["samples"] if sample["valid"]),
        "median_ms": median(durations_ms),
        "mean_ms": mean(durations_ms),
        "min_ms": min(durations_ms),
        "max_ms": max(durations_ms),
        "sensitivity_rows": len(result.sensitivities),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }))
PY
```

### Observed local probe

Using the same deterministic target and three measured repetitions after one
warmup, the current workspace produced:

```text
samples  median_ms  repetitions_ms
50       7.168       7.169, 7.168, 7.031
100      14.345      14.345, 13.979, 14.713
250      37.151      37.151, 36.410, 49.833
```

This was a local Python 3.13 run on the current dirty worktree. The values are
repeatability evidence for the deterministic core only; they are not a
performance budget, production SLO, browser result, or medical claim.

This probe includes Pydantic response validation performed by
`run_missing_piece` when the baseline is supplied as the serialized mapping
returned by `run_ensemble`. It excludes fixture loading, request construction,
HTTP, persistence, frontend rendering, and process startup. A future checked-
in benchmark runner should also report standard deviation or p95, payload
size, repository revision, and dirty-worktree status, while retaining the
same timing boundary.

The focused correctness gate remains:

```bash
PYTHONPATH=. uv run --project . --extra dev pytest -q \
  python/hearttwin/tests/test_missing_piece_engine.py \
  python/hearttwin/tests/test_missing_piece_engine_review.py
```

Correctness must pass before timing is interpreted. In particular, the tests
cover deterministic repeatability, target-specific output, input immutability,
persisted projection-base authority, unavailable samples, and the explicit
information-gain boundary.

## Scalar overlay boundary

M8 produces scalar, target-specific records: raw local sensitivity,
dimensionless normalized response, empirical parameter spread, uncertainty-
impact heuristic, evidence priority score, and completeness metadata. These
may support a labelled scalar annotation beside an existing metric or an
inspector row when the UI preserves the target, units, provenance, and
unavailable state.

M8 does **not** produce a pointwise pressure-volume uncertainty envelope,
waveform confidence band, voxel/mesh uncertainty field, or a new 3D geometry.
Scalar q05/q95 values must not be stretched across a PV loop or painted as a
spatially varying heart overlay. Existing Split Heart or PV visuals can show a
scalar status/legend only; they must not imply uncertainty at every point of a
curve or surface. Any future pointwise overlay requires canonical pointwise
data, a separately reviewed uncertainty representation, and its own benchmark
and visual QA evidence.

## Honest blockers and open gates

- No M8 benchmark result has been recorded here yet. The command above is a
  reproducible local synthetic probe, not evidence until it is run and its raw
  output is retained with host and revision metadata.
- There is no M8-specific checked-in benchmark runner or persisted benchmark
  artifact yet. The inline command is intentionally narrow and should not be
  treated as a long-term reporting interface.
- The command does not measure SQLite persistence, API serialization, HTTP
  latency, worker-thread behavior, or restart safety. Those require separate
  stages and must not be folded into the deterministic core number.
- No concurrency, memory-peak, large-payload, or hosted-capacity measurement
  has been established. The `O(NP)` transient sensitivity record set is the
  main reason to add a memory probe before increasing sample counts.
- Browser/WebGL frame-time, accessibility, and visual overlay evidence remain
  environment-dependent gates. A successful HTTP request or TypeScript build
  is not browser performance or accessibility evidence.
- The current environment has previously lacked the audio library required by
  the available Chromium harness, and Firefox is not available. Browser timing
  and accessibility results therefore remain unverified until a compatible
  browser/AT environment is supplied.
- No threshold, safe sample-count recommendation, clinical utility claim, or
  information-gain claim is made from this document.
