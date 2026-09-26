# M6 Scenario Preset Review

Date: 2026-09-26  
Scope: scenario preset audit only. No implementation files were changed. M7
Split Heart and M8 Missing Piece remain out of scope.

## Verdict

**PASS WITH VALIDATION REQUIREMENTS.** M4 provides a small, bounded parameter
vocabulary that can support user-facing Shadow Trial presets. A preset must be
a declarative `ScenarioDefinition` value: metadata plus explicit parameter
values and units. It must not contain a second physiology implementation,
derive effects in the browser, or replace the persisted M5.5 sample parameters.

The backend remains the authority for validating and applying the preset. The
frontend bounds and constructors are useful for early input feedback, but they
are not a trust boundary.

## M4 bounded parameter vocabulary

The definitions are in
[`web/lib/twin/scenario/parameters.ts`](../../../web/lib/twin/scenario/parameters.ts#L31-L74)
and are also summarized by [`M4_PARAMETER_RANGES.md`](../M4_PARAMETER_RANGES.md).

| Parameter | Unit | Inclusive bounds | Preset requirement |
| --- | --- | ---: | --- |
| `heart_rate_bpm` | `bpm` | 30–200 | `value` must be finite and within bounds |
| `preload_index` | `index` | 0–1.5 | `value` must be finite and within bounds |
| `afterload_index` | `index` | 0–2 | `value` must be finite and within bounds |
| `contractility_index` | `index` | 0–1.5 | `value` must be finite and within bounds |
| `systemic_vascular_resistance_index` | `index` | 0–2 | `value` must be finite and within bounds |

Bounds are inclusive. Unknown keys, non-finite values, and values outside the
declared interval are not valid preset inputs. The index unit is
dimensionless; it is not interchangeable with bpm, mL, mmHg, or L/min.

## Current M6 request shape

The public TypeScript shape is
[`web/types/shadow-trial.ts`](../../../web/types/shadow-trial.ts#L21-L34):

```text
ShadowTrialRequest
  baseline_ensemble_id: string
  scenario: ShadowTrialScenarioDefinition
    id: string
    label: string
    description?: string | null
    origin_snapshot_id?: string | null
    parameters: ShadowTrialScenarioParameter[]
      parameter: string
      baseline?: number
      value: number
      delta?: number
      unit?: string
    created_at?: string | null
  metrics?: ShadowTrialMetricId[]
```

The backend mirrors this contract in
[`python/hearttwin/shadow_trial_contracts.py`](../../../python/hearttwin/shadow_trial_contracts.py#L72-L109,
#L169-L184). The trial engine loads the persisted ensemble, validates the
scenario, and applies each change to the matching sample's parameter vector;
it does not create a new sampled scenario ensemble
([`shadow_trial_engine.py`](../../../python/hearttwin/shadow_trial_engine.py#L114-L144)).

## Requirements for a bounded preset

Every preset should satisfy these requirements before it is offered to the
Shadow Trial UI or sent to the API:

1. **Declarative only.** Store an identifier, label, optional description,
   origin metadata, and an ordered list of parameter changes. A preset may
   select `value` and record `unit`; it must not store computed states,
   distributions, deltas for output metrics, formulas, or a precomputed trial
   result.
2. **Known keys and unique changes.** Use only the five M4 parameter keys and
   include each key at most once. The backend contract rejects duplicate
   parameter IDs; preset definitions should be rejected before submission as
   well.
3. **Finite bounded values.** Validate each `value` against the inclusive table
   above. Reject `NaN`, infinities, strings, and implicit coercion. Do not clamp
   invalid values silently.
4. **Consistent change metadata.** When `baseline` is supplied, it must itself
   be finite and within the same parameter bounds. When both `baseline` and
   `delta` are supplied, require `delta == value - baseline` within the
   contract tolerance. A preset must not use a stale baseline merely to make a
   delta appear plausible.
5. **Exact units.** Use `bpm` for heart rate and `index` for the four index
   parameters. Missing units may be accepted only where the backend contract
   explicitly supplies the known parameter unit; a preset should include the
   unit to make the serialized request auditable.
6. **Origin binding.** A preset may be reusable across compatible synthetic
   ensembles, but it must not claim a different `origin_snapshot_id`. The
   active baseline ensemble and its origin remain the source of truth. A preset
   must not replace that origin with a frontend default or with a sampled twin.
7. **No population rebasing.** Omitted parameters mean “leave every baseline
   sample's persisted parameter unchanged,” not “fill from
   `DEFAULT_SCENARIO_PARAMETERS`.” The scenario application must preserve each
   sample's complete latent vector and change only explicitly declared keys.
8. **Stable serialization.** Presets should serialize with stable field names,
   numeric values, parameter order, and version metadata. Labels and
   descriptions are for display and provenance; they must not affect numerical
   evaluation except where included intentionally in the trial identity.

## Frontend boundary: no canonical math

The frontend may validate controls, construct a preset, display bounds, and
submit the request. It must not:

- reimplement the M5.5 evaluator or compute scenario EDV, ESV, SV, EF, CO, MAP,
  PV area, or effect distributions;
- call the M4 `propagateScenario` evaluator as the authoritative M6 trial
  engine;
- apply a preset to every sample using one shared/default parameter vector;
- resample a seed or synthesize a second population;
- clamp out-of-range values and present the clamped result as the user's
  original preset;
- infer clinical benefit, harm, treatment ranking, or efficacy from a preset or
  its displayed sign category.

The existing M4 helpers remain appropriate for input vocabulary and local
validation. The numerical authority is the versioned Python M5.5 projection
seam, as recorded in
[`M6_SCENARIO_APPLICATION_REVIEW.md`](M6_SCENARIO_APPLICATION_REVIEW.md).

## Current implementation checks

| Check | Current result | Evidence / implication |
| --- | --- | --- |
| M4 key and bound lookup | **Pass** | `SCENARIO_PARAMETER_DEFINITIONS` and `validateScenarioParameter` reject unknown, non-finite, and out-of-range values. |
| Duplicate parameter rejection | **Pass** | Python `ScenarioDefinition.unique_parameters` rejects duplicates. |
| Scenario value validation | **Pass** | M6 `_validate_scenario` checks supported keys, finite values, inclusive bounds, and supplied unit compatibility. |
| Same-sample application | **Pass** | `_apply_scenario` starts from `sample.parameters`, changes only declared keys, and uses the canonical Python evaluator. |
| `baseline`/`delta` validation at the API boundary | **Partial** | The Pydantic contract checks consistency when both are present; the active engine validation does not independently require a supplied baseline or delta to be present/correct. Presets must emit consistent metadata, and the API contract remains the final gate. |
| Frontend numerical authority | **Pass with boundary** | The active M6 panel consumes backend results; M4 propagation remains a separate UI implementation and must not be used for trial math. |

## Required preset review gate

Before a preset is marked ready, review its serialized request against this
checklist:

- [ ] Only the five M4 parameter keys are used.
- [ ] Every value and supplied baseline is finite and within its exact bounds.
- [ ] Units match the parameter table.
- [ ] No duplicate parameter entries exist.
- [ ] `delta` matches `value - baseline` whenever both are supplied.
- [ ] `origin_snapshot_id` is absent or matches the active persisted baseline.
- [ ] No computed state, effect, distribution, formula, or clinical language is
      embedded in the preset.
- [ ] The backend receives the preset as data and performs all canonical
      scenario application and effect computation.
- [ ] The UI labels the result as a hypothetical/simulated Shadow Trial and
      retains the safety disclaimer.

This review does not authorize M7 split-heart presentation, M8 missing-piece
reasoning, treatment recommendation, or final product redesign.
