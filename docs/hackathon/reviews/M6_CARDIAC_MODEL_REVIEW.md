# M6 Cardiac Model Review

Date: 2026-09-26
Scope: read-only cardiac-model audit of the M5.5 Python ensemble, the repaired
M6 Shadow Trial projection path, and frontend numerical-authority boundaries.
No implementation files were changed. M7 Split Heart and M8 Missing Piece are
out of scope.

## Verdict

**PASS for M6 formula authority and paired projection after the projection-base
repair; CONDITIONAL for full numerical closure.**

The active M5.5 ensemble and M6 Shadow Trial use the Python projection contract
`m5.5-ensemble-projection-v1`. M5.5 persists the exact normalized projection
base on every sample. M6 copies that base and the sample's full parameter vector,
replaces only the declared scenario targets, and evaluates the counterfactual
without drawing a second population. The persisted baseline outputs remain the
baseline authority for delta calculation, preventing sampled parameters from
being applied twice.

The remaining conditions are bounded architectural or representation risks,
not evidence of M6 resampling:

1. The repository retains an importable legacy TypeScript evaluator with
   formulas that differ from Python. It is not on the active backend ensemble
   or M6 production path, but it must remain quarantined.
2. M6 computes `map_mmhg` in the canonical output map, while the projected
   `CardiacTwinState` does not contain a dedicated MAP measurement and therefore
   retains its source blood-pressure fields. Consumers must use the returned
   effect output for MAP and must not infer a scenario MAP from the state alone.
3. M6 imports private Python helpers (`_evaluate` and `_derived_state`) from
   `ensemble.py`. This is numerically coherent today but is a maintenance seam
   for a future versioned public projection function.

## Formula authority

The active authority is the Python M5.5 ensemble implementation:

| Responsibility | Authority | Audit result |
| --- | --- | --- |
| Parameter support and public bounds | `python/hearttwin/ensemble.py:22-28` | Five bounded input proxies are declared once for the backend. |
| Origin normalization | `python/hearttwin/ensemble.py:320-346` | HR, EDV, EF, ESV, index fallbacks, and MAP baseline are normalized deterministically. |
| Projection formula | `python/hearttwin/ensemble.py:365-375` | EDV, ESV, SV, CO, EF, and MAP are derived from explicit inputs and the persisted base. |
| Ensemble sampling | `python/hearttwin/ensemble.py:349-362,416-429` | Seeded sampling occurs only in M5.5; M6 does not call the sampler. |
| Scenario projection | `python/hearttwin/shadow_trial_engine.py:114-144` | M6 delegates to the canonical Python evaluator with a sample-local base. |
| Paired delta calculation | `python/hearttwin/shadow_trial_engine.py:189-203` | `scenario - baseline`, with baseline values read from persisted sample outputs. |

The low-level pure cardiac helpers in
`python/hearttwin/tools/cardiac_state.py` remain the repository's explicit
formula library for SV, EF, CO, MAP, RR, and related indices. M5.5's bounded
ensemble projection is a separate versioned educational projection contract;
M6 does not introduce a competing cardiac formula.

## M5.5 projection behavior

For each ensemble request, `_baseline` creates a deterministic projection base
from the origin state. The base includes:

- HR clamped to 30–220 bpm;
- EDV clamped to 40–400 mL;
- EF clamped to 5–90 percent;
- ESV clamped to 5 mL through EDV minus 1 mL;
- preload, afterload, contractility, and SVR index fallbacks of 1.0; and
- MAP as `DBP + (SBP - DBP) / 3`.

`_evaluate(base, parameters)` then applies parameter ratios to this base:

- EDV scales with the preload ratio and remains bounded to 40–400 mL;
- ESV uses the bounded afterload and contractility terms;
- SV is `EDV - ESV`;
- CO is `HR × SV / 1000` in L/min;
- EF is `SV / EDV × 100` in percent; and
- MAP is a bounded base-MAP projection using SVR and CO ratios.

M5.5 stores `projection_base` alongside `parameters`, `outputs`, validity, and
the derived state. This persisted field is the critical repair that gives M6 a
stable origin for every sample rather than forcing it to reconstruct a base
from an already projected state.

## M6 scenario application and pairing

The repaired path has the required paired semantics:

1. `run_shadow_trial` validates the persisted `EnsembleResponse`, scenario
   parameter keys, bounds, finiteness, and optional units.
2. Samples are sorted by stable `(sample.id, sample.index)` order. Array order
   is not the pairing key.
3. `_apply_scenario` copies the sample's persisted projection base and full
   sampled parameter vector, then replaces only declared scenario values.
4. The same Python `_evaluate` formula is called once for the counterfactual.
   No random generator, seed draw, or second ensemble is created.
5. An identity scenario returns a deep copy of the persisted sample state and
   outputs, preserving exact zero deltas.
6. For a non-identity scenario, the derived state is copied before scenario
   fields are updated. Baseline state and baseline outputs remain untouched.
7. Deltas are calculated from the persisted baseline output map and the
   scenario output map. The engine does not recalculate the baseline from the
   projected state.

This is specifically covered by
`python/hearttwin/tests/test_shadow_trial_engine.py::test_mixed_sample_scenario_uses_persisted_projection_base_once`.
The test compares each pair with `_evaluate(sample["projection_base"],
scenario_parameters)`, which is the correct no-double-application check.

Scenario `value` is an absolute target for the selected parameter. The optional
`baseline` and `delta` fields are provenance metadata and consistency checks;
they are not applied as a second adjustment to each heterogeneous sample. A
single scenario target is therefore intentionally evaluated against each
sample's own latent parameter value.

## Invariants and rejection behavior

The current gates are coherent across M5.5 and M6:

| Invariant | Enforcement | Assessment |
| --- | --- | --- |
| Finite sampled parameters, projection base, and outputs | `EnsembleSample` validators | PASS |
| EDV greater than ESV, positive SV, EF within 0–100 | M5.5 acceptance check after `_evaluate` | PASS for accepted baseline samples |
| Scenario parameter key, bound, and unit | `_validate_scenario` | PASS |
| Baseline EDV/ESV availability | `_apply_scenario` | PASS; missing values invalidate the pair |
| Missing requested output metric | M6 pair-level rejection | PASS; no fabricated zero or unchanged effect |
| Invalid baseline pair retention | `PairedTwinResult` and trial counts | PASS; reasons remain inspectable |
| Zero valid pairs | trial status `failed`, empty effect summaries | PASS; no effect distribution is fabricated |
| Baseline immutability | deep copies and focused regression tests | PASS |

The canonical evaluator's bounds make valid counterfactual outputs finite and
preserve the volume ordering used by M5.5. M6 relies on that shared evaluator
rather than duplicating a second invariant implementation. The engine does not
run a separate post-evaluation invariant function over every scenario output;
this remains an implementation coupling worth preserving in tests when the
projection contract changes.

`pv_loop_area_index` is intentionally not generated by the M5.5 scalar
projection. Requesting it produces invalid pairs when unavailable, rather than
copying a baseline value or inventing a PV effect. This is the correct current
boundary for the M6 scalar experiment.

## State/output representation caveat

The scenario output map contains `map`, and `_read_metric` correctly prefers
that output for `map_mmhg`. However, `_derived_state` only projects HR, EDV,
ESV, EF, SV, and CO. M6 updates the hemodynamic index fields and RR interval,
but it does not rewrite systolic or diastolic blood pressure fields to encode
the derived MAP. Consequently:

- API effect distributions for MAP are authoritative when `map_mmhg` is
  requested;
- the pair's typed scenario state is not a complete MAP projection; and
- UI or downstream code must not calculate a scenario MAP from the retained
  blood-pressure fields and call it the M6 scenario output.

The current M6 panel avoids this ambiguity by requesting MAP for the effect
distribution while showing only EF, SV, and CO in pair cards. Any future MAP
state display needs an explicit contract decision and unit-bearing field.

## Frontend formula-drift audit

### Active path: no M6 formula drift

The active frontend ensemble seam sends distributions to the Python API through
`web/lib/twin/ensemble/backend.ts:39-67` and maps the response in
`web/lib/twin/ensemble/adapter.ts:5-64`. The active Shadow Trial panel
(`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:79-145`) sends the
declarative scenario definition, then formats backend pairs, distributions,
units, and warnings. It does not compute cardiac outputs, paired deltas,
quantiles, or direction categories.

`web/lib/twin/ensemble/backend.ts` uses
`baselineScenarioParameters` only to construct prior/distribution request
means. The browser result is not used as the M6 cardiac calculation.

### Residual quarantine requirement

`web/lib/twin/scenario/propagation.ts:133-161` and
`web/lib/twin/ensemble/runner.ts:115-171` contain a legacy TypeScript
implementation. It is numerically different from Python, including the ESV
afterload coefficient (`base.sv * 0.55` versus Python's
`base.edv * 0.25`), lower-bound handling, and rounding. The runner is imported
by historical tests but not by the active backend ensemble or M6 panel. This is
not an active M6 drift finding; it is a medium architectural risk that must not
be reconnected to production behavior without an explicit version/parity
decision and new vectors.

## Verification evidence

Focused read-only validation from `/home/923873155/BeatIT`:

```text
PYTHONPATH=. uv run --project . --extra dev pytest -q \
  python/hearttwin/tests/test_ensemble.py \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_shadow_trial_golden.py \
  python/hearttwin/tests/test_shadow_trial_reproducibility.py

67 passed in 0.43s
```

The evidence covers M5.5 deterministic projection behavior, M6 mixed-distribution
projection-base use, no-op exact zeros, order-independent pairing,
immutability, invalid-pair retention, missing-PV behavior, golden vectors, and
serialized replay. The repository remained dirty with pre-existing M5.5/M6
work; this review added documentation only.

## Recommended closure

Before declaring complete numerical closure, keep these items explicit in the
M6 handoff:

1. Preserve `projection_base` as a versioned M5.5 sample field and keep the
   mixed-distribution regression test.
2. Keep the TypeScript runner and M4 evaluator quarantined from active M6
   execution; do not claim cross-language formula parity.
3. Treat M6 MAP as an output-map metric until a dedicated state contract is
   approved.
4. If the private helper seam is refactored, preserve the exact
   `m5.5-ensemble-projection-v1` vectors and rerun the golden fixtures.

No M7 or M8 work is recommended or authorized by this review.
