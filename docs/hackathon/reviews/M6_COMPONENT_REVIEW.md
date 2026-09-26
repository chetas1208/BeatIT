# M6 Component Inspector Review

**Agent:** M6 agent #20
**Date:** 2026-09-26
**Scope:** read-only review of the active M6 `ShadowTrialPanel`, its TypeScript
types, and the backend paired-result contracts. No production code was changed.
M7 Split Heart and M8 Missing Piece are out of scope.

## Verdict

**CONDITIONAL PASS — bounded scalar inspection is safe, but it is not a
component-level anatomical viewer.** The backend returns complete typed
`CardiacTwinState` objects for each pair, while the active component exposes
only EF, stroke volume, and cardiac output. That narrow surface is appropriate
for M6. It must remain explicit that omitted anatomy, unavailable metrics, and
held visualization context are not silently reconstructed from the values that
are present.

## Reviewed data boundary

The backend `PairedTwinResult` carries the following fields for one identity-
preserving pair:

| Field | Component-safe meaning | Not implied |
| --- | --- | --- |
| `sample_id`, `baseline_twin_id`, `scenario_twin_id` | Pair and twin identifiers | An anatomical part, spatial registration, or second physical heart |
| `baseline_state`, `scenario_state` | Typed scalar/twin state payloads from the backend | A measured or rendered scenario anatomy |
| `baseline_parameters`, `scenario_parameters`, `parameters` | Latent/input parameter records used by the deterministic projection | Patient anatomy, tissue measurements, or clinical observations |
| `deltas`, `delta_units` | Backend-computed scenario-minus-baseline scalar effects | Clinical benefit, harm, efficacy, or treatment response |
| `valid`, `rejection_reasons` | Pair validity and retained failure explanation | Permission to fill missing values or ignore an invalid pair |

The backend `EffectDistribution` separately provides finite deltas, summary
statistics, quantiles, category counts, and a metric-specific neutral
tolerance. The component may format these values, but it must not recalculate
them or infer values for metrics not present in the response.

## What the active component displays

Evidence reviewed in
[`ShadowTrialPanel.tsx`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx):

- The distribution list requests and displays EF, stroke volume, cardiac
  output, heart rate, and MAP (`METRICS`, lines 10–16).
- The pair inspector displays only EF, stroke volume, and cardiac output from
  `state.measurements` (lines 53–70).
- Pair identity and the no-resampling statement are shown as text (lines
  73–74).
- Invalid pairs remain selectable and show their backend rejection reasons
  (line 74).
- A failed trial announces that no effect summary is available while retaining
  invalid pairs for inspection (lines 131–136).
- The PV boundary explicitly says that pointwise PV samples and a PV
  uncertainty envelope are unavailable (line 137).

Consequently, the component must not be described as rendering every field in
`CardiacTwinState`. The backend state includes optional patient context,
electrophysiology, hemodynamics, tissue state, operating environment, source
maps, and optional CT segmentation; none of those fields is a paired anatomical
measurement in the current M6 component.

## Component-level data limits

### Scalar values only

The inspector is a scalar comparison surface. It may show the backend-provided
value and unit for a selected pair, and it may show the returned delta or
distribution summary. It must not derive a new measurement from another
field, apply a frontend physiology formula, or turn an input parameter into a
measured value.

### No fabricated anatomy

The component must not invent or imply any of the following from EF, SV, CO,
HR, MAP, EDV, ESV, or parameter values:

- chamber size, wall thickness, valve state, vessel geometry, perfusion, or
  regional tissue condition;
- a scenario-specific 3D heart, anatomical deformation, or spatial alignment
  between baseline and scenario;
- CT segmentation, tissue abnormalities, or component-level structures when
  those fields are absent from the response;
- a pressure-volume trajectory or loop area from scalar endpoints.

The existing single-heart visualization is presentation context, not a
baseline/scenario anatomical pair. It must remain labeled as hypothetical or
simulated where applicable and must not be updated with fabricated
scenario-specific anatomy.

### Parameters are not anatomy

`baseline_parameters` and `scenario_parameters` describe the deterministic
projection inputs. They are useful for audit and provenance, but a UI label
must not call them observed physiology or anatomical measurements. The
`parameters` field is a compatibility copy of the baseline parameter record in
the current contract; it is not an additional source of truth.

## Unit display rules

The backend effect contract is authoritative for delta units:

| Metric | Effect unit | Safe display wording |
| --- | --- | --- |
| Ejection fraction | `percentage_points` | “percentage points” |
| Stroke volume | `mL` | “mL” |
| Cardiac output | `L/min` | “L/min” |
| Heart rate | `bpm` | “bpm” |
| MAP | `mmHg` | “mmHg” |
| EDV / ESV | `mL` | “mL” |
| PV loop area index | `index` | “index”, only when actually available |

The distinction between a state value and a delta is important: an EF state
may be displayed with `%`, while an EF delta must be described as **percentage
points**, not percent change. The current formatter maps the backend
`percentage_points` token to that wording for distributions. Any future
component-level display must preserve the same distinction and must not
silently substitute a unit based on the metric name alone.

## Safe handling of unavailable fields

The safe behavior is fail closed:

1. A missing or non-finite scalar is rendered as **“unavailable”**; it is not
   replaced with zero, a prior value, or a value copied from the other member.
2. The backend marks a pair invalid when a requested metric is unavailable in
   either baseline or scenario state and retains the corresponding
   `rejection_reasons`. The component must preserve and display that reason.
3. An empty effect distribution means that no summary is available. It must not
   be presented as a zero-effect distribution.
4. A failed trial or zero-valid-pair result must keep the invalid pair records
   inspectable and must not show an effect interpretation.
5. `pv_loop_area_index` and pointwise PV data are unavailable in the active
   M5.5-backed surface unless the backend explicitly returns finite values and
   units. The component must never infer them from EF, SV, EDV, ESV, a held PV
   shape, or a percentile.
6. Optional anatomy-bearing fields such as CT segmentation remain absent when
   absent in the backend state. Absence is not evidence of normal anatomy.

The backend contract also requires explicit units, finite deltas, and a
canonical safety disclaimer. The component should preserve those guarantees
and should not downgrade an unavailable or invalid field to an ordinary
successful measurement row.

## Provenance and safety wording

The component can identify the trial, baseline ensemble, same-sample pairing,
and warnings from the response provenance. It must retain the visible
“hypothetical simulation” and “not clinical advice or treatment guidance”
boundary. Direction categories such as positive, near-zero, and negative are
descriptive simulation categories only; they are not anatomical findings or
clinical value judgments.

## Validation evidence

- Source inspection covered the active M6 panel, `web/types/shadow-trial.ts`,
  `PairedTwinResult`, `EffectDistribution`, `ShadowTrialResult`, and the
  `CardiacTwinState`/`MeasuredValue` schemas.
- The focused M6 backend/API contract and engine tests were already reported
  green by the surrounding M6 review work; this task changed documentation
  only.
- No frontend, backend, M7, or M8 files were modified.

## Review conclusion

The current inspector has a defensible M6 component boundary when it is
presented as a scalar paired experiment surface. The critical invariant is
that the component displays only backend-provided values and clearly exposes
unavailable/invalid states. Any future request for paired anatomy, split-heart
rendering, or missing-structure explanation belongs to a separately approved
milestone and is not part of this review.
