# M6 PV Boundary Review

Date: 2026-09-26  
Scope: M5.5 PV uncertainty limits and the active M6
`ShadowTrialPanel`; documentation-only review. No code, M7, or M8 work is
included.

## Verdict

The current M6 surface is honest when it is limited to scalar paired outputs.
M5.5 stores scalar plausible-twin outputs, not a pressure-volume trajectory for
each accepted sample. Therefore M6 may compare scalar measurements returned by
the paired backend, but it must not present those values as a pointwise PV
uncertainty envelope.

There is one contract caveat: `pv_loop_area_index` is listed in the M6 metric
union and has a reader in the engine, but it is not supplied by the current
M5.5 ensemble projection. It is unavailable for the active PV boundary. A
request for it must remain unavailable or fail closed; it must never be filled
with zero or inferred from EF, SV, EDV, ESV, or a held PV curve.

## Evidence reviewed

- The M5.5 ensemble sample contains sampled parameters, scalar outputs, and a
  typed state; it has no per-sample PV-loop trajectory
  ([`M5_5_PV_AUDIT.md`](../M5_5_PV_AUDIT.md#backend-data-actually-available)).
- The ordinary backend visualization can contain one PV curve, but that curve
  is a separate single-visualization channel, not ensemble PV data
  ([`M5_5_PV_AUDIT.md`](../M5_5_PV_AUDIT.md#backend-data-actually-available)).
- `pvUncertaintyEnvelope` exposes scalar EF/SV distributions and hard-codes
  `pointwiseLoopAvailable: false`
  ([`web/lib/twin/ensemble/pvEnvelope.ts`](../../../web/lib/twin/ensemble/pvEnvelope.ts)).
- `ShadowTrialPanel` requests EF, SV, CO, HR, and MAP; its pair inspector shows
  scalar EF, SV, and CO only. It explicitly says that M5.5 has no pointwise PV
  samples and that the baseline shape is held
  ([`web/components/twin/shadow-trial/ShadowTrialPanel.tsx`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L10-L16),
  [`ShadowTrialPanel.tsx`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L57-L74),
  [`ShadowTrialPanel.tsx`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L131-L139)).

## Allowed scalar comparisons

All allowed deltas use the backend rule `scenario - baseline` for the same
paired twin. They are descriptive simulation outputs, not clinical estimates
or value judgments.

| Scalar | Unit | M6 use | PV interpretation |
| --- | --- | --- | --- |
| Ejection fraction | percentage points | Pair values, deltas, and distribution summaries | PV-linked scalar only; not a curve coordinate or envelope |
| Stroke volume | mL | Pair values, deltas, and distribution summaries | PV-linked scalar only; not a loop width estimate |
| EDV | mL | Allowed when present and finite in both members of a pair | Scalar volume endpoint only; not a volume-axis trajectory |
| ESV | mL | Allowed when present and finite in both members of a pair | Scalar volume endpoint only; not a volume-axis trajectory |
| Cardiac output | L/min | Allowed scalar effect metric | Hemodynamic scalar, not PV uncertainty |
| Heart rate | bpm | Allowed scalar effect metric | Input/output scalar, not PV uncertainty |
| MAP | mmHg | Allowed scalar effect metric | Pressure scalar, not pressure-axis trajectory |

For valid paired samples, M6 may report the raw scalar delta, median, mean,
q05/q25/q75/q95, and positive/near-zero/negative direction counts using the
documented metric-specific tolerances. The q05–q95 summary is a distribution of
paired scalar deltas; it is not a confidence interval, credible interval,
probability, or pointwise PV band.

The held baseline PV shape may be shown as context for the selected snapshot.
It must be labeled as held baseline context and must not be described as the
scenario loop, a sampled twin loop, or an uncertainty envelope.

## Unavailable comparisons

The active M5.5/M6 contract does not support any of the following:

- pressure at aligned volume, phase, or time across paired twins;
- a per-sample PV trajectory for baseline and scenario states;
- q05–q95 pressure or volume values at PV points;
- a pointwise PV uncertainty ribbon, fan, or confidence/credible band;
- an ensemble distribution of loop shape, loop width, loop area, or stroke work;
- a scenario PV loop obtained by rescaling or morphing the held baseline loop;
- a PV result obtained by converting scalar EF/SV percentiles into pressure or
  volume coordinates;
- a clinical or treatment interpretation of any scalar direction category.

`pv_loop_area_index` is also unavailable in the current M5.5-backed trial even
though it appears in `ShadowTrialMetricId`. The engine's state lookup does not
create an authoritative scenario loop or area. Until both baseline and
scenario loop areas come from the same versioned canonical evaluator, this
metric must not be advertised as an available PV comparison.

## Current panel assessment

The panel currently protects the main boundary:

1. Its requested metric list contains no PV-loop metric.
2. Its pair inspector compares scalar EF, SV, and CO values, not curves.
3. Its PV notice states that pointwise PV samples are absent and that no PV
   uncertainty envelope is fabricated.
4. Its distribution cards describe scalar percentiles across valid paired
   plausible twins and use direction-only category language.

This is an M6 scalar comparison surface, not a PV visualization surface. The
existing M5.5 `pvUncertaintyEnvelope` behavior is the required model: expose
only the scalar EF/SV summaries and set pointwise PV availability to false.

## Anti-fabrication checks

The following checks are required for the current boundary and for any future
change that might expose PV uncertainty:

| Check | Required invariant | Current status |
| --- | --- | --- |
| Metric allowlist | The panel requests only explicitly supported scalar IDs; unavailable PV metrics do not silently default | Pass for the active panel; `pv_loop_area_index` remains a contract caveat |
| Pair authority | Every scalar delta uses the same baseline sample and its corresponding scenario twin; no new scenario draw is accepted | Pass and visible in the panel provenance text |
| Scalar/curve separation | Scalar percentiles are rendered as scalar text/cards, never as PV coordinates or curve widths | Pass in `pvEnvelope` and the panel |
| Capability flag | Pointwise PV availability remains false unless the backend supplies canonical pointwise data | Pass: `pointwiseLoopAvailable: false` |
| Held-shape labeling | A copied baseline curve is labeled held baseline context and cannot be used as scenario or uncertainty data | Pass in M5.5 labels and M6 panel notice |
| Missing data | Missing PV values produce unavailable/invalid output, not a zero, copied value, or inferred value | Required fail-closed behavior; must remain covered by tests |
| Canonical provenance | A future PV envelope requires evaluator/version, coordinate alignment, sampling policy, and origin provenance for every accepted sample | Required before enabling pointwise PV; not available in M5.5 |
| Numerical validity | Future pointwise arrays must be finite, non-empty, equal-length, and aligned between baseline and scenario pairs before aggregation | Required before enabling pointwise PV; not available in M5.5 |

Before pointwise PV is ever enabled, focused fixtures should prove at least:

- scalar-only M5.5 input cannot produce a curve or envelope;
- missing baseline or scenario PV data fails closed;
- mismatched point counts or coordinate grids fail closed;
- pair order changes do not change the resulting envelope;
- a no-op paired trial preserves the exact pointwise curve;
- all aggregated points retain the same coordinate/provenance contract.

Until those conditions are met, the correct UI is the current scalar surface
plus an explicit “pointwise PV unavailable” statement. This review does not
authorize M7 split-heart behavior, M8 missing-piece behavior, or any redesign
of the PV model.

## Review result

**PASS WITH BOUNDARY NOTE.** The active panel does not fabricate pointwise PV
uncertainty. Scalar EF/SV and other explicitly returned scalar effects are
allowed within the limits above. Pointwise PV comparisons and
`pv_loop_area_index` remain unavailable until an authoritative, versioned
per-sample PV contract exists.
