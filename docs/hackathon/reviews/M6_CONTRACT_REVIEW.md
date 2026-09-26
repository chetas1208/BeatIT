# M6 Contract Review — Shadow Trial Engine

Date: 2026-09-26  
Scope: read-only review of the current M6 contracts, paired engine, identity
helpers, persistence, API routes, fixtures, and focused tests. No implementation
or API files were changed by this review. M7 Split Heart and M8 Missing Piece
are out of scope.

## Verdict

The current M6 surface is a useful scaffold and its focused tests are green,
but the contract is not ready to claim paired-trial correctness. The highest
risk is numerical: `shadow_trial_engine.py` evaluates a scenario from a
sample's already-projected state while supplying that sample's latent
parameters again. With non-fixed distributions this can apply a sampled
parameter twice. The contract tests do not detect this because they check
repeatability and shape, not the expected same-baseline projection.

The next integration gate should be **BLOCKED pending the numerical authority
repair and the P0 contract fixes below**. The API and store are present in the
latest workspace; the older statements in `M6_PREFLIGHT.md` that they do not
exist are stale and should be reconciled with this review.

## Single-authority recommendation

Use the Python M5.5 deterministic projection as the only numerical authority:

1. Keep the M5.5 evaluator and baseline representation in `python/hearttwin/ensemble.py`
   as the source of truth for baseline and counterfactual scalar outputs.
2. Expose one supported, public projection seam for M6. It should accept the
   immutable origin baseline plus one complete parameter vector, and return the
   canonical scalar outputs and typed state projection. M6 should orchestrate
   pairing, validity, deltas, and descriptive statistics around that seam; it
   must not recreate formulas.
3. Treat `python/hearttwin/shadow_trial_contracts.py` as the backend wire
   contract. The TypeScript M4 definitions remain frontend input/rendering
   types and must be generated from or tested against the backend shape; they
   must not calculate a competing trial result.
4. Make the baseline ensemble content-addressed or immutable before it can be
   a trial input. A trial identity must include the exact baseline content
   digest, scenario digest, engine version, selected metrics, and category
   tolerances.

The current engine imports private M5.5 helpers (`_baseline`, `_evaluate`, and
`_derived_state`) at `python/hearttwin/shadow_trial_engine.py:11-18`. That is
closer to one numerical implementation than a duplicate formula, but private
imports are not a stable authority boundary and do not solve the base-state
double-application problem.

## Evidence executed

The following focused command passed:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q \
  python/hearttwin/tests/test_shadow_trial_api.py \
  python/hearttwin/tests/test_shadow_trial_contracts.py \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_shadow_trial_identity.py \
  python/hearttwin/tests/test_shadow_trial_golden.py \
  python/hearttwin/tests/test_shadow_trial_store.py

29 passed, 8 warnings in 1.46s
```

The passing tests cover model validation, basic pairing, no-op immutability,
input-order replay, one invalid baseline pair, one unavailable metric, route
creation/retrieval, one executable golden vector, and restart-safe trial-store
serialization. They do not close the gaps below.

An additional read-only probe compared the current mixed-distribution output
with a projection from the original M5.5 origin baseline and the same sample's
parameters:

```text
sample-0 sampled_preload=1.0308192827392924 actual_sv_delta=-3.998470578734114 expected=-7.278918961399839
sample-1 sampled_preload=0.9946340264793716 actual_sv_delta=-6.333893368971502 expected=-10.133267968163551
sample-2 sampled_preload=0.9418419854205957 actual_sv_delta=-12.908042884600391 expected=-14.863019738628424
```

The probe used the existing `run_ensemble`, `run_shadow_trial`, `_baseline`,
and `_evaluate` functions with a three-sample seeded ensemble. It is evidence
of a contract failure, not a proposed change to the physiology formulas.

## Invariant gap register

### P0 — Numerical same-baseline invariant is not enforced

Evidence: `shadow_trial_engine.py:126-152` calls `canonical_baseline(sample.state)`
and then evaluates `target_parameters`, which contains the sample's already
sampled parameters plus the scenario changes. M5.5 generated `sample.state`
from the origin baseline and those sampled parameters at
`ensemble.py:410-425`. Consequently, a sampled preload, contractility, or
SVR can be applied once when the sample is made and again when the scenario is
projected. The implementation's comment at `shadow_trial_engine.py:222-224`
does not establish the required invariant.

Required test: for every valid pair, independently project from the immutable
origin baseline with the exact persisted baseline parameter vector, change only
the declared scenario parameters, and assert exact/tolerance equality with the
scenario outputs. Include mixed normal, uniform, and empirical distributions.

### P0 — M4 `ScenarioDefinition` is only partially represented

The M4 TypeScript contract requires an immutable origin object and required
`baseline`, `value`, `delta`, `unit`, and `createdAt` fields at
`web/lib/twin/scenario/types.ts:35-52`. The Python M6 contract makes
`baseline`, `delta`, and `unit` optional at
`python/hearttwin/shadow_trial_contracts.py:71-80`; scenario origin and
creation time are also optional at `:91-101`. The engine accepts the missing
fields and fills only `origin_snapshot_id` later at `:275-279`.

This prevents the record from proving what the requested change was relative
to, and it permits a scenario to be accepted without a stable origin
timestamp or complete M4 lineage. `baseline` is not compared with the origin
parameter or the paired sample parameter, so even a supplied but incorrect
baseline is accepted.

Required test: reject missing required M4 fields, reject a `delta` that does
not match `value - baseline`, and reject a supplied baseline that does not
match the declared scenario origin semantics. Preserve the full immutable
origin reference or explicitly version the reduced backend contract.

### P0 — Trial identity omits inputs that change the result

`_trial_id` at `shadow_trial_engine.py:179-188` hashes the ensemble ID,
scenario JSON, sorted metric IDs, and two version strings. It does not hash the
baseline ensemble payload/content, scenario engine/config digest, or category
tolerances. The engine accepts a `neutral_tolerance` override at `:195-210`.
The same ensemble and scenario therefore produce the same fingerprint while
different tolerances produce different positive/neutral/negative categories.

The direct probe demonstrated:

```text
tolerance_fingerprint_equal True
tolerance_categories (0, 0, 3) (0, 3, 0)
```

Required test: changing any result-affecting option must change the trial
fingerprint, while canonical reordering of semantically unordered inputs must
not. Persist the per-metric tolerance policy in the definition/provenance.

### P0 — Baseline persistence is replaceable, so an ID is not an immutable input

`SQLiteEnsembleStore.save` explicitly performs an upsert at
`python/hearttwin/storage/ensemble_store.py:88-115`. M6 trusts a retrieved
ensemble by ID and does not verify a baseline content digest against the trial
identity. A later replacement under the same ensemble ID can change sample
parameters, outputs, and provenance while leaving the M6 trial ID formula
unchanged. The M6 shadow-trial store is create-once, but that protects the
result record, not the baseline it references.

Required test: create a baseline, run and persist a trial, replace or mutate
the baseline record under the same ID, then require a digest mismatch or an
explicit immutable-input error. Do not silently replay against changed input.

### P1 — Pair identity does not prove same index and same latent parameters

The engine sorts samples and derives `scenario-{sample_id}` at
`shadow_trial_engine.py:211-243`. `PairedTwinResult` only requires that
`baseline_twin_id == sample_id` and that the scenario ID is different at
`shadow_trial_contracts.py:186-216`. It does not carry or validate the
baseline sample index, baseline parameter digest, scenario parameter digest,
or an origin/ensemble digest. `parameters` duplicates
`baseline_parameters` without a validator requiring equality. The standalone
identity helper is tested, but the engine does not use its full pair-index
validation path.

Required test: tamper with sample index, parameter vector, or scenario ID and
require contract rejection. Store a pair-level identity record containing
trial ID, scenario digest, baseline sample ID/index, and baseline parameter
digest.

### P1 — Cross-object result consistency is incomplete

`ShadowTrialResult.validate_result` at
`shadow_trial_contracts.py:315-341` checks count reconciliation, unique sample
IDs, baseline ensemble provenance, the disclaimer, and effect values. It does
not require:

- `definition.id == definition_id` when a definition is present;
- definition baseline/origin/provenance to match the result and its pairs;
- the selected metric set to be present and identical in the definition,
  pair deltas, and distributions;
- `status == "failed"` when `valid_pairs == 0`, or `status == "complete"`
  when at least one valid pair exists;
- empty effect distributions when no valid pairs exist;
- a complete `delta_units` map matching every delta and the canonical unit;
- a scenario twin ID format that binds it to this trial/scenario.

An invalid pair can also retain partial deltas because the engine appends a
metric delta before a later metric becomes unavailable at
`shadow_trial_engine.py:226-239`. The effect summary excludes the invalid pair,
but the pair inspector can still display a partial invalid comparison without
a machine-readable missing-metric contract.

Required tests should construct tampered Pydantic payloads directly, not only
exercise the happy-path engine.

### P1 — Provenance is missing the audit digests and execution identity

`ShadowTrialProvenance` at `shadow_trial_contracts.py:111-137` contains useful
origin, seed, version, evidence, and assumption fields, but not:

- a provenance schema version;
- baseline ensemble content/digest and parameter-distribution digest;
- scenario definition digest and scenario engine version;
- pairing policy and pairing digest;
- trial execution timestamp distinct from origin/scenario creation time;
- sample index/parameter digests for every pair;
- the RNG/runtime algorithm identity for the source ensemble.

`created_at` is optional and the engine falls back to the ensemble provenance
timestamp at `shadow_trial_engine.py:256-269`, conflating origin/ensemble
creation with trial execution. `origin_provenance` remains
`list[dict[str, Any]]`, so its schema and finite/JSON-safe contents are not
validated.

Required test: serialize, restart, and compare the complete provenance envelope
and pair digest byte-for-byte; require distinct normalized origin, scenario,
and trial timestamps.

### P1 — PV loop area is an advertised metric without a canonical scenario output

`pv_loop_area_index` is included in the metric literal and unit map at
`shadow_trial_contracts.py:22-44`, but M5.5 `_evaluate` returns no PV-loop
quantity (`ensemble.py:359-369`). `_read_metric` falls back to the copied state
at `shadow_trial_engine.py:85-92`; a scenario can therefore appear valid with
a zero PV delta merely because the state field was carried forward, not because
the scenario evaluator computed it. The current missing-PV test covers only a
state with no value.

Required decision/test: either remove PV from the M6 metric contract until a
canonical evaluator produces it, or mark it explicitly as unchanged/uncomputed
and exclude it from effect distributions. Never present a copied field as a
computed counterfactual.

### P1 — Tolerance and category policy are not fully contractual

`NEAR_ZERO_TOLERANCES` is a Python constant at
`shadow_trial_contracts.py:45-54`, but the result does not retain the selected
policy except inside each distribution. The direct engine API can apply one
global override to all metrics, while the HTTP request cannot express or
retrieve that choice as part of the request definition. `EffectDistribution`
does not explicitly require `neutral_tolerance` to be finite, and empty
distributions may still contain non-null quantile values.

Required test: reject non-finite tolerances, validate empty quantiles are null,
persist per-metric thresholds, and assert categories are descriptive signs
only—not benefit/harm judgments.

### P2 — Golden and adversarial coverage is narrower than the fixture inventory

Six JSON fixtures exist under `fixtures/golden/shadow_trials`, but
`test_shadow_trial_golden.py` executes only
`fixed-baseline-afterload.json`. The remaining fixed-baseline-simple,
mixed-distribution, bounded-invalid, zero-delta, reproducibility, and
synthetic-demo fixtures are declarative inventory, not executable golden gates.
The current engine tests also do not assert the independent same-origin
projection described in the P0 numerical invariant.

Required test: parameterize the golden test over all six fixtures, with explicit
expected values for at least the mixed-distribution, invalid-pair, no-op,
reproducibility, and synthetic provenance cases.

### P2 — Documentation and implementation status have drifted

The current API imports and routes M6 at `python/hearttwin/api.py:41-43,207-274`,
and the current focused suite reports 29 passing tests. However,
`docs/hackathon/M6_PREFLIGHT.md:123-141` still says there is no API or
persistence integration and describes the store as replaceable/upsert-based.
The latter remains true for the baseline store but not for the new shadow store.
The M6 plan also marks several integrated files as pending. These stale claims
can mislead the completion gate and should be updated after the P0 repairs,
without treating the current green tests as numerical closure.

## What is already sound

- Pydantic models use `extra="forbid"` in the M6 contract module.
- Scenario parameter IDs are unique and supplied `delta` values are checked
  against `value - baseline`.
- Pair and result counts reconcile for engine-produced results.
- Effect units and positive/neutral/negative category counts are validated for
  non-empty distributions.
- The engine sorts baseline samples, preserves invalid pairs with reasons, and
  does not mutate the input object in the tested no-op path.
- The shadow-trial SQLite store is file-backed, create-once, and accepts an
  exact canonical replay while rejecting a changed payload; its focused store
  tests pass.
- API responses include the canonical safety disclaimer, and the implementation
  uses descriptive effect language rather than clinical value claims.

These are useful foundations, not a waiver for the numerical and identity
gates above.

## Recommended completion gate

Do not mark M6 ready until the following contract tests pass in addition to the
current 29-test focused suite:

1. Origin-baseline same-sample projection matches independently recomputed
   expected outputs for mixed distributions.
2. Required M4 scenario fields and origin lineage are enforced.
3. Baseline, scenario, tolerance, engine, and pair digests are persisted and
   included in stable trial identity.
4. Baseline replacement under an existing ID is rejected or detected.
5. Pair index/parameter tampering is rejected; invalid pairs have explicit
   missing-metric semantics.
6. Result/definition/status/unit/provenance cross-field tampering is rejected.
7. PV loop area is either canonically computed or removed from the advertised
   M6 metric set.
8. All six golden fixtures execute, and restart retrieval reproduces the same
   result and provenance.

Until then, the accurate status is: **M6 contract scaffold implemented;
paired numerical and provenance closure pending.**
