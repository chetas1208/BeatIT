# M6 Scenario Application Review

Date: 2026-09-26  
Scope: audit only; no shared implementation changed; M6 implementation has not started.

## Verdict

M4 is reusable as a **declarative scenario definition, parameter vocabulary,
provenance shape, and safety boundary**. It is not currently a safe M6 execution
seam.

The active M5.5 numerical authority is Python
(`m5.5-ensemble-projection-v1`). The frontend M4 evaluator remains a separate
implementation with known formula and rounding differences, as recorded in
[`M5_5_NUMERICAL_AUDIT.md`](../M5_5_NUMERICAL_AUDIT.md). M6 must therefore add a
backend-owned, non-resampling adapter/application function rather than invoking
`web/lib/twin/scenario/propagation.ts` for authoritative shadow-trial math.

## M4 contracts that can be reused

### `ScenarioDefinition`

Defined in [`web/lib/twin/scenario/types.ts:45-52`](../../../web/lib/twin/scenario/types.ts):

| Field | Meaning | M6 handling |
| --- | --- | --- |
| `id` | Stable user-visible scenario identity | Persist and include in trial identity; do not use a newly generated ID per pair |
| `label`, `description` | Human-readable hypothetical scenario metadata | Display metadata only; never use as numerical input |
| `origin` | Immutable source snapshot metadata and cloned state | Validate against the persisted ensemble origin; do not replace it with a sampled twin |
| `parameters` | Bounded parameter changes with baseline, value, delta, and unit | Translate to the backend application request after strict validation |
| `createdAt` | Origin-normalized deterministic timestamp in current propagation | Preserve the supplied definition timestamp; do not use request wall-clock time for numerical identity |

`origin` is `ObservedOriginMetadata` at
[`types.ts:22-30`](../../../web/lib/twin/scenario/types.ts). It carries snapshot
ID, patient/case ID, timestamp, a detached state, provenance, evidence IDs, and
optional snapshot quality. M6 must preserve all of these fields and must never
upgrade `synthetic`, `derived`, or `interpolated` origin quality to `observed`.

`ScenarioParameterChange` is defined at
[`types.ts:35-42`](../../../web/lib/twin/scenario/types.ts). Its `delta` is a
recorded change from `baseline` to `value`; it is not an independent input. An
adapter should verify the relationship and reject inconsistent records rather
than silently recomputing or accepting the supplied delta.

## Exact reusable M4 functions

| Function / value | Location | Safe reuse in M6 |
| --- | --- | --- |
| `SCENARIO_PARAMETER_DEFINITIONS` | [`parameters.ts:31-74`](../../../web/lib/twin/scenario/parameters.ts) | Canonical frontend labels, units, and public bounds for request validation/documentation. Backend must independently validate against its authoritative contract. |
| `getScenarioParameterDefinition` | [`parameters.ts:94-98`](../../../web/lib/twin/scenario/parameters.ts) | Lookup only; useful for translating a definition and checking its declared unit. |
| `isValidScenarioParameter` / `validateScenarioParameter` | [`parameters.ts:100-121`](../../../web/lib/twin/scenario/parameters.ts) | Early UI/input validation only. Never the sole backend validation gate. |
| `createScenarioParameterChange` | [`parameters.ts:150-171`](../../../web/lib/twin/scenario/parameters.ts) | Safe constructor for a frontend definition. Its output is still untrusted at the API boundary. |
| `forkSnapshot` / `createSnapshotFork` | [`fork.ts:61-79`](../../../web/lib/twin/scenario/fork.ts) | Safe immutability pattern for local copies. M6 backend must deep-copy/validate its own Pydantic state; it cannot rely on a browser object or frontend freeze. |
| `M4_CAUSAL_GRAPH` | [`propagation.ts:52-91`](../../../web/lib/twin/scenario/propagation.ts) | Explanation metadata and path labels only. It is not an executable M6 physiology engine. |
| `baselineScenarioParameters` | [`propagation.ts:225-233`](../../../web/lib/twin/scenario/propagation.ts) | UI distribution/request configuration only. Do not use it to overwrite each persisted sample's latent parameters. |
| `serializeScenarioDefinition` / `deserializeScenarioDefinition` | [`persistence.ts:265-280`](../../../web/lib/twin/scenario/persistence.ts) | Versioned browser persistence format. It is not a backend trial persistence contract and must not be treated as server-side validation. |
| `scenarioVisualization`, `scenarioHeartBinding`, `scenarioPvLoop` | [`visualization.ts:10-53`](../../../web/lib/twin/scenario/visualization.ts), [`heart.ts:8-27`](../../../web/lib/twin/scenario/heart.ts), [`pv.ts:23-35`](../../../web/lib/twin/scenario/pv.ts) | Presentation projections only. They must not generate M6 baseline/scenario values or effect statistics. |

### Python deterministic primitives

These existing pure functions are reusable building blocks when an approved
backend application seam calls them with explicit, validated inputs. They are
not a replacement for that seam, and M6 must not duplicate their behavior in
TypeScript:

| Function | Location | Units / boundary |
| --- | --- | --- |
| `compute_stroke_volume` | [`cardiac_state.py:13-17`](../../../python/hearttwin/tools/cardiac_state.py) | EDV/ESV in `mL`; returns `mL`; rejects invalid volume ordering |
| `compute_ejection_fraction` | [`cardiac_state.py:20-25`](../../../python/hearttwin/tools/cardiac_state.py) | Volumes in `mL`; returns `%` |
| `compute_cardiac_output` | [`cardiac_state.py:28-34`](../../../python/hearttwin/tools/cardiac_state.py) | HR in `bpm`, SV in `mL`; returns `L/min` |
| `compute_map` | [`cardiac_state.py:37-41`](../../../python/hearttwin/tools/cardiac_state.py) | SBP/DBP in `mmHg`; returns `mmHg` |
| `compute_afterload_index`, `compute_svr_index` | [`cardiac_state.py:44-61`](../../../python/hearttwin/tools/cardiac_state.py) | Inputs include `mmHg` and `L/min`; returns dimensionless indices |
| `compute_preload_index`, `compute_contractility_index` | [`cardiac_state.py:64-74`](../../../python/hearttwin/tools/cardiac_state.py) | Returns dimensionless indices; these are educational proxies |
| `compute_rr_from_hr` | [`cardiac_state.py:92-96`](../../../python/hearttwin/tools/cardiac_state.py) | HR in `bpm`; returns `ms` |
| `simulate_pv_loop` / `generate_pressure_volume_loop` | [`hemodynamics.py:64-77`](../../../python/hearttwin/tools/hemodynamics.py), [`hemodynamics.py:190-227`](../../../python/hearttwin/tools/hemodynamics.py) | Volumes in `mL`, pressures in `mmHg`, EF in `%`, work in `J`; educational visualization output |
| `generate_cardiac_cycle` | [`hemodynamics.py:230-281`](../../../python/hearttwin/tools/hemodynamics.py) | Time in `ms`, volume in `mL`, pressure in `mmHg`, flow in `mL/s`, CO in `L/min` |

The M6 adapter should call these only through a versioned backend service that
also validates `CardiacTwinState`, records warnings, preserves `MeasuredValue`
source metadata, and emits the canonical safety disclaimer. It must not call
`run_ensemble` for scenario application because that function owns sampling as
well as evaluation.

## Unit semantics

The M4 parameter vocabulary is defined in
[`parameters.ts:11-20`](../../../web/lib/twin/scenario/parameters.ts):

| Quantity | Unit | Public bounds | Role |
| --- | --- | --- | --- |
| `heart_rate_bpm` | `bpm` | 30–200 | Manipulable input proxy |
| `preload_index` | dimensionless `index` | 0–1.5 | Manipulable input proxy |
| `afterload_index` | dimensionless `index` | 0–2 | Manipulable input proxy |
| `contractility_index` | dimensionless `index` | 0–1.5 | Manipulable input proxy |
| `systemic_vascular_resistance_index` | dimensionless `index` | 0–2 | Manipulable input proxy |

The M4 propagation graph declares these derived/output units at
[`propagation.ts:61-72`](../../../web/lib/twin/scenario/propagation.ts):

| Output | Unit | M6 requirement |
| --- | --- | --- |
| End-diastolic volume (`edv`) | `mL` | Keep separate from stroke volume and preserve the unit in the pair record |
| End-systolic volume (`esv`) | `mL` | Same |
| Stroke volume (`sv`) | `mL` | Compute paired delta in `mL` |
| Cardiac output (`co`) | `L/min` | Compute paired delta in `L/min`; never compare its raw number to `mL` |
| Mean arterial pressure (`map`) | `mmHg` | Preserve as a distinct observable and unit |

M4 also writes ejection fraction as `%` and RR interval as `ms` in the derived
state at [`propagation.ts:170-188`](../../../web/lib/twin/scenario/propagation.ts).
The typed state fields and their measurement units are defined in
[`web/types/heart.ts:25-58`](../../../web/types/heart.ts). An M6 adapter must
carry units on every effect metric and reject missing or incompatible units;
display labels are not unit conversion.

## Deterministic propagation seam assessment

`propagateScenario` at
[`propagation.ts:236-322`](../../../web/lib/twin/scenario/propagation.ts) is a
complete frontend M4 operation: it validates duplicate/unknown/bounded inputs,
reads a snapshot baseline, creates a detached scenario state, builds a
`ScenarioDefinition`, emits causal deltas, and returns a deterministic result.
It is useful as a contract reference and local UI behavior reference.

It is **not** safe as the active M6 numerical seam because:

1. It executes in the frontend, while M5.5 assigns numerical authority to
   Python.
2. Its evaluator is an independent implementation. The M5.5 audit records
   differences from the Python evaluator in afterload sensitivity, lower-bound
   clamping, and output rounding.
3. It accepts a partial input list and fills omitted parameters from the snapshot
   baseline. That is reasonable for a single UI scenario, but M6 must make the
   full per-sample parameter vector explicit so no sample is accidentally
   re-based on the population/origin state.
4. Its PV and 3D helpers are visual projections, not paired physiological
   execution functions.

The Python low-level cardiac functions remain pure and reusable individually:
`cardiac_state.py` contains the deterministic cardiac calculations and
`hemodynamics.py` contains the educational PV/cycle calculations. The current
Python `run_ensemble` path also samples and evaluates in one function at
[`ensemble.py:410-429`](../../../python/hearttwin/ensemble.py); calling it for
M6 would incorrectly resample a counterfactual population. M6 needs a separate
non-sampling application seam factored behind the same versioned authority.

## Safe M6 adapter requirements

The future adapter should satisfy all of the following before implementation is
accepted:

1. **Declarative input:** accept a versioned `ScenarioDefinition`-equivalent
   request. Labels/descriptions are metadata; only validated parameter keys,
   values, and units enter numerical execution.
2. **Authoritative validation:** validate finite values, exact supported keys,
   no duplicates, public bounds, units, baseline/value/delta consistency, and
   scenario-definition identity in Python. Frontend validation is advisory.
3. **Stable source:** load one persisted M5.5 ensemble and verify the requested
   origin snapshot/ensemble IDs and physiology/distribution versions before
   applying anything.
4. **Pair-preserving application:** for every accepted baseline sample, use that
   sample's own full `parameters` vector and stable sample ID. Apply the same
   scenario change to that vector/state. Never call the sampler, draw a new
   seed, or construct an independent scenario ensemble.
5. **Stable pair identity:** persist `baseline_sample_id`, `scenario_sample_id`,
   `ensemble_id`, `scenario_definition_id`, and model version. A pair is valid
   only when the scenario identity is derived from the corresponding baseline
   sample, not merely from array position.
6. **Immutable inputs:** do not mutate the stored ensemble, origin snapshot, or
   baseline sample. Create a derived scenario state and retain rejection reasons
   for invalid pairs.
7. **Lineage preservation:** carry origin quality, origin provenance, evidence
   IDs, seed, parent scenario ID, and safety disclaimer forward. Synthetic replay
   must remain synthetic and visibly labeled.
8. **Metric contract:** calculate paired deltas only from canonical backend
   outputs, with explicit units. Reuse the existing backend output names and
   reject mixed-unit or missing-output pairs.
9. **Determinism:** identical persisted ensemble, definition, and version must
   produce identical pairs, deltas, categories, and serialized results. Do not
   use wall-clock time, request order, or browser ordering in numerical identity.
10. **Presentation boundary:** M4 causal graph/path metadata may explain a pair,
    but frontend PV/3D projections must remain labeled educational projections
    and must not be used to derive effect statistics.
11. **Safety language:** preserve the canonical safety disclaimer and describe
    positive/neutral/negative regions as descriptive simulation categories, never
    as treatment benefit, harm, diagnosis, or clinical efficacy.

## M6 readiness decision

| Gate | Status | Evidence |
| --- | --- | --- |
| M4 declarative definition and parameter vocabulary | Reusable | `types.ts`, `parameters.ts`, `propagation.ts` reviewed |
| Immutable scenario-origin pattern | Reusable with backend revalidation | `fork.ts`, `propagateScenario`, persistence contracts |
| Active canonical numerical authority | Available for M5.5 baseline only | Python `ensemble.py`, M5.5 audit |
| Backend non-sampling scenario application seam | **Missing** | No current Python function accepts one existing sample plus a scenario definition |
| Frontend M4 evaluator as M6 authority | **Rejected** | Known cross-layer divergence documented in `M5_5_NUMERICAL_AUDIT.md` |
| M6 paired trial implementation | Not started | This review performed no implementation work |

M6 should remain at preflight until the missing backend application seam and its
paired golden vectors are designed. This review does not authorize changes to
shared formulas or implementation.

## Verification evidence

Commands run from the repository:

```text
cd web && npx tsc --noEmit
PASS

cd web && node --experimental-strip-types --loader ./tests/alias-loader.mjs \
  --test ./lib/twin/scenario/__tests__/propagation.test.ts \
  ./lib/twin/scenario/__tests__/history.test.ts
2 passed, 2 failed
```

The focused Node run is not a clean M4 pass: the propagation test is blocked by
the existing Node 22 strip-only harness rejecting a TypeScript parameter
property in `web/lib/twin/time/clocks.ts:367`; the history suite also exposes an
existing expectation/implementation mismatch in its first test. No source was
changed to hide either result.

The related deterministic Python regression set was run with Python 3.13:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q \
  python/hearttwin/tests/test_cardiac_formulas.py \
  python/hearttwin/tests/test_cardiac_formulas_golden.py \
  python/hearttwin/tests/test_hemodynamics.py \
  python/hearttwin/tests/test_ensemble.py
150 passed in 0.23s
```

## Changed files

- `docs/hackathon/reviews/M6_SCENARIO_APPLICATION_REVIEW.md` — this audit.
- `Decisions.md` — recorded the M6 adapter boundary and non-authority of the
  frontend evaluator.
- `Progress.md` — recorded the audit evidence and remaining preflight blocker.

No shared implementation, formula, API, frontend component, or test file was
edited.
