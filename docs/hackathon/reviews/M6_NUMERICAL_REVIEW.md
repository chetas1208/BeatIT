# M6 Numerical Pairing / No-Resampling Review

Date: 2026-09-26  
Scope: read-only review of the active Python Shadow Trial engine and the M5.5
canonical ensemble evaluator. No implementation files were edited by this
review.

## Verdict

**CONDITIONAL PASS for numerical pairing and formula authority.** The active
engine preserves same-sample pairing, is independent of baseline sample array
order, does not resample, and produces scalar deltas that match the canonical
M5.5 evaluator exactly in the independent probe below. The no-op path is also
exact and non-mutating.

The review does not support an unconditional identity/reproducibility sign-off
until the following are resolved or explicitly accepted as contract decisions:

1. Reversing the order of scenario parameter declarations preserves numerical
   deltas but changes the trial ID and serialized payload because the raw list
   order is included in the trial identity.
2. `scenario_twin_id` is generated as `scenario-<sample_id>` in the active
   engine, so it is not globally namespaced by trial ID even though the identity
   helper supports a namespaced two-argument form.
3. The canonical MAP output is used for the returned delta, but the projected
   `scenario_state` does not update systolic/diastolic BP fields. Consumers that
   derive MAP from that state rather than from the paired output can observe a
   stale baseline pressure representation.

These are identity/state-representation findings, not evidence of a duplicated
physiology formula in the active delta path.

## Reviewed implementation

- [`shadow_trial_engine.py`](../../../python/hearttwin/shadow_trial_engine.py)
  - `_apply_scenario`: lines 114–144
  - trial identity: lines 147–156
  - sorted same-sample execution: lines 180–221
  - baseline/scenario metric extraction and raw deltas: lines 190–203
- [`ensemble.py`](../../../python/hearttwin/ensemble.py)
  - canonical evaluator: lines 365–375
  - canonical typed-state projection: lines 378–396
  - baseline sampling and persisted `projection_base`: lines 416–431
- [`shadow_trial_identity.py`](../../../python/hearttwin/shadow_trial_identity.py)
  - compact and trial-namespaced identity forms: lines 40–63
- [`shadow_trial_contracts.py`](../../../python/hearttwin/shadow_trial_contracts.py)
  - pair invariants: lines 192–222

## Invariant results

| Invariant | Result | Evidence |
| --- | --- | --- |
| Same baseline sample identity | PASS | Every returned pair had `sample_id == baseline_twin_id`; baseline parameters and baseline state matched the corresponding persisted sample. |
| Scenario identity follows the same sample | PASS with namespace caveat | Each scenario ID was `scenario-<sample_id>`; see F-2 for cross-trial collision risk. |
| No resampling | PASS | The engine imports/calls `canonical_evaluate` and `canonical_derived_state`; it does not import `random` or call `run_ensemble`. It copies each sample’s persisted parameters and `projection_base`. |
| Baseline sample order independence | PASS | Reversing the 12-sample input array produced the same trial ID, fingerprint, and complete serialized result. |
| No-op behavior | PASS | Empty scenario produced exact zero deltas, equal baseline/scenario states, `status=complete`, and left the input ensemble unchanged. |
| Formula authority | PASS for returned scalar metrics | Independent comparison across 12 samples and EF, SV, CO, HR, MAP, EDV, and ESV reported maximum delta error `0.0` versus `ensemble._evaluate`. |
| Scenario declaration order independence | FINDING F-1 | Reversing two semantically independent parameter declarations preserved deltas but changed trial ID and payload. |
| Typed MAP state projection | FINDING F-3 | Returned MAP deltas use canonical evaluator outputs, but the scenario state’s BP fields remain baseline values. |

## Independent verification

The following focused regression set was run from the repository root:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_shadow_trial_reproducibility.py \
  python/hearttwin/tests/test_shadow_trial_golden.py \
  python/hearttwin/tests/test_shadow_trial_identity.py \
  python/hearttwin/tests/test_shadow_trial_contracts.py

23 passed, 8 warnings
```

An independent probe constructed a deterministic 12-sample ensemble from
`fixtures/hearttwin/manual_baseline.json`, applied an afterload target of
`1.25`, and compared the result to `_evaluate(sample.projection_base,
scenario_parameters)` for every valid sample. It reported:

```text
{
  'samples': 12,
  'valid_pairs': 12,
  'max_delta_error_vs_canonical_evaluate': 0.0,
  'identity_failures': [],
  'scenario_parameters_changed_only': True
}
{'order_independent_payload': True, 'same_trial_id': True}
{'noop_all_zero': True, 'noop_states_equal': True, 'input_unchanged': True, 'noop_status': 'complete'}
```

A runtime wrapper around the engine’s imported canonical evaluator observed five
evaluator calls for five valid pairs, with no sampler symbol present in the
engine source:

```text
{
  'canonical_evaluate_calls': 5,
  'valid_pairs': 5,
  'call_count_matches_valid_pairs': True,
  'sampler_symbol_present_in_engine': False
}
```

## Numerical authority assessment

The authority boundary is correctly placed for the returned effects:

1. M5.5 persists each sample’s `parameters`, `projection_base`, `outputs`, and
   typed state in `EnsembleSample` (`ensemble.py:188–220`).
2. M6 starts from the persisted per-sample parameter vector and changes only
   declared scenario keys (`shadow_trial_engine.py:122–128`).
3. M6 calls the existing `_evaluate` implementation rather than reimplementing
   its preload, afterload, contractility, SVR, EDV, ESV, SV, EF, CO, HR, and MAP
   formulas (`ensemble.py:365–375`).
4. Baseline metric values come from persisted `sample.outputs`; scenario metric
   values come from canonical evaluator outputs. This avoids evaluating the
   already-projected baseline a second time (`shadow_trial_engine.py:190–203`).
5. The independent max-error check was exactly zero, including MAP, where the
   engine reads the canonical `scenario_outputs["map"]` for the delta.

This is the correct numerical shape for a paired counterfactual: one persisted
population, one corresponding scenario evaluation per valid sample, and no
second random draw.

## Findings

### F-1 — Scenario parameter declaration order changes deterministic identity

**Severity: P1 reproducibility contract / P2 numerical behavior.**

Two definitions with the same ID, label, and two changes but opposite parameter
list order produced identical per-sample deltas, while both the trial ID and
serialized result differed:

```text
{
  'scenario_parameter_order_same_payload': False,
  'scenario_parameter_order_same_trial_id': False,
  'scenario_parameter_order_same_deltas': True
}
```

The reason is visible at `shadow_trial_engine.py:147–155`: `_trial_id` hashes
`scenario.model_dump(...)`, which retains the input list order. `ScenarioDefinition`
only requires unique parameter IDs (`shadow_trial_contracts.py:104–109`); it does
not define that order as meaningful. If request order is not intended to be
semantic, identity normalization should sort changes by parameter ID before
hashing and before any reproducibility claim. If order is intentionally part of
the persisted definition, document that contract explicitly.

### F-2 — Compact scenario IDs are not trial-namespaced

**Severity: P1 persisted identity risk.**

The active loop calls `scenario_sample_id(sample.id)` at
`shadow_trial_engine.py:208–218`, yielding `scenario-<sample_id>`. The helper’s
two-argument form can instead yield `<trial_id>-scenario-<sample_id>`
(`shadow_trial_identity.py:40–53`), but the engine does not use it. Therefore the
same baseline sample ID paired in two different scenarios receives the same
scenario twin ID. The result itself retains trial-level context, so the current
API can still retrieve a pair by trial ID, but the compact twin ID is not a
globally unique persisted identity.

This is not a numerical mismatch, but it weakens the claim that each persisted
pair is independently addressable and makes downstream joins unsafe if they use
`scenario_twin_id` without the trial ID.

### F-3 — MAP delta is authoritative, but the scenario typed state retains BP

**Severity: P1 state-contract mismatch.**

The canonical evaluator returns `map`, and `_read_metric` prioritizes that output
for `map_mmhg` (`shadow_trial_engine.py:59–80`). Consequently the reported MAP
delta passed the canonical comparison with zero error. However, canonical
`_derived_state` updates EF, SV, CO, HR, EDV, and ESV only
(`ensemble.py:378–396`); it does not update systolic or diastolic BP. The M6
engine then uses that projection without adding a MAP/BP projection. In the
independent probe, the MAP reconstructed from `scenario_state` BP fields differed
from canonical scenario MAP by up to `6.945301614219829 mmHg`.

The safe current boundary is therefore: use returned paired metric/output fields
for MAP, and do not derive MAP from `scenario_state` until its BP representation
is made consistent. The frontend or any later consumer should not treat the
scenario state’s BP fields as the M6 MAP result.

### F-4 — Scenario `value` is the numerical target; `baseline` is not sample-checked

**Severity: P2 contract clarity.**

`ScenarioParameterChange` validates finite values and the internal relationship
between supplied `baseline`, `value`, and `delta` when all are present
(`shadow_trial_contracts.py:72–89`). Execution nevertheless applies the absolute
`value` to every sample (`shadow_trial_engine.py:122–128`); it does not verify that
the supplied `baseline` equals each sample’s parameter or interpret `delta` as an
additive per-sample change. This matches the current M6 decision that scenario
values are applied to each existing sample, but the API documentation should keep
the absolute-target semantics explicit so a request such as “+15%” is not
mistakenly encoded as a universal absolute value.

## Review conclusion and gate

The core numerical invariant is satisfied: **M6 is same-sample, deterministic,
and formula-authoritative for returned scalar effects, with no resampling.** The
focused tests and independent probes provide reproducible evidence for that
claim.

Recommended gate status: **NUMERICAL CORE PASS; IDENTITY/STATE CONTRACTS
CONDITIONAL.** Before treating the full numerical review as closed, resolve or
explicitly accept F-1 through F-3, especially the MAP state mismatch and the
non-namespaced scenario twin ID if pair records will be consumed outside the
trial-scoped API.

No M7 Split Heart or M8 Missing Piece behavior was reviewed or introduced here.

## Post-review resolution

The lead canonicalized scenario parameter declaration order before trial
identity/fingerprinting and changed persisted scenario twin IDs to the
trial-namespaced form `<trial_id>-scenario-<sample_id>`. The remaining MAP
typed-state finding is intentionally bounded: returned MAP deltas use the
canonical evaluator output, while consumers must not reconstruct MAP from the
scenario state's unchanged systolic/diastolic fields.
