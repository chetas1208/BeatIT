# M7 Signal Boundary — ECG and Electrical Visual Layers

Status: **documentation boundary for M7 split-heart consumption**  
Scope: ECG context, ECG-derived scalar fields, and the 3D electrical layer. This
document does not change the signal pipeline or authorize new physiology.

## Boundary in one sentence

BeatIT may show supplied ECG context, deterministic features derived from a
supplied waveform, and a clock-driven educational electrical animation. It must
not present the animation or an HR/RR projection as a measured ECG, a patient-
specific conduction map, or a diagnosis.

## Existing signal sources

The backend and frontend use related, but not identical, source vocabularies.
Keep the source label attached to the value or visual whenever the signal is
shown.

| Source/state | What exists | Safe display label | Safe claim |
|---|---|---|---|
| `measured` | An observed ECG context or waveform with provenance. The temporal frontend can expose `ECG · measured` for a non-synthetic selected snapshot with RR data. | `ECG · measured` or `Measured ECG context` | The selected snapshot contains observed ECG context. This label alone is not evidence that a raw waveform is currently available; show a waveform only when waveform data/chart payload is present. |
| `extracted` | An ECG field or feature extracted from supplied material. The frontend type supports this kind; the backend also preserves field source, method, confidence, and file references. | `ECG · extracted` or `Extracted ECG feature` | The displayed scalar was extracted/derived from supplied input. Do not call it a directly measured waveform. |
| `reported` | A reported rhythm label or ECG statement. The electrophysiology agent sanitizes wording and retains it as reported wording. | `Reported ECG descriptor` / `reported rhythm label` | This is a supplied report descriptor, not a new clinical conclusion. |
| `waveform_estimated` | The deterministic ECG feature tool analyzes a selected numeric lead, preferring Lead II, and can produce a downsampled chart payload plus R-peak, RR, and optional QTc features. | `Waveform-derived features` with lead, sampling rate, method, and confidence | Features were estimated by the educational waveform pipeline. Do not call the preview a clinical-grade ECG interpretation. |
| `simulated` / `simulated_visualization` | A visual or timing representation when the source is synthetic, a report-extracted RR value, or no waveform is available. The backend always produces an electrical visual payload. | `Simulated electrical visualization` / `simulated timing context` | The display is a deterministic educational projection. It is not a measured waveform. |
| `missing` / `unknown` | No supported ECG waveform or usable ECG context at the selected cursor. | `ECG unavailable` / `ECG context unknown` | Absence is shown as absence. Do not fill the gap with a generated ECG trace. |

The canonical frontend signal kind is defined in
[`web/lib/twin/ecg/index.ts`](../../web/lib/twin/ecg/index.ts) as
`measured | extracted | simulated | missing`. Backend electrophysiology
outputs additionally use `reported`, `waveform_estimated`,
`simulated_visualization`, and `unknown`. A consumer must not silently map a
reported label or a derived scalar to a measured waveform.

## What the existing layers actually render

### ECG context and scalar features

The temporal provider creates one ECG context object for the selected snapshot.
It can carry a timestamp, kind, rhythm label, RR interval, QRS duration, QTc,
and provenance. The snapshot quality determines whether the current provider
marks the context as `simulated` or `measured`; this is context metadata, not a
promise that raw samples are available. The provider does not synthesize a
waveform from those scalar fields.

The backend electrophysiology agent has two separate outputs:

- A chart payload is produced only after a valid numeric waveform/lead is
  selected and analyzed. It records the selected lead, sampling rate, duration,
  signal preview, R-peak indices, RR intervals, an HR estimate, source, and
  approximate confidence. The display string is intentionally
  `simulated ECG chart`, and the feature tool is explicitly educational rather
  than a clinical ECG interpreter.
- An electrical visual payload is always produced. It contains a bounded beat
  interval, a dimensionless `wave_speed`, optional conduction-delay and
  instability scores, a confidence value, and the display string
  `simulated electrical visualization`. This payload is a visual contract, not
  a recorded electrical field.

The scalar fields may be shown with their units and provenance when present:

- RR interval: `ms`, with the source/method attached.
- QRS, QT, and QTc: `ms`, only when supplied or deterministically derived by
  the existing pipeline; no morphology should be drawn from them.
- R-peak confidence: an approximate `[0, 1]` detector confidence, not clinical
  certainty.
- Arrhythmia instability and conduction-delay scores: bounded,
  dimensionless display proxies. They describe the implemented rule, not a
  diagnosis or a validated clinical score.

When fewer than two R peaks are detected, the waveform tool returns a warning
and does not invent waveform-derived RR, HR, or QTc. The UI should preserve
that missing/insufficient-data state.

### 3D electrical layer

The current electrical layer is a visualization-only overlay:

- Six registry nodes are shown: SA node, AV node, Bundle of His, left bundle
  branch, right bundle branch, and Purkinje network.
- The paths are fixed semantic paths through those nodes. Their positions are
  normalized proxy coordinates on the procedural heart, not patient-specific
  anatomy.
- Node activation uses fixed normalized phases, and the layer reads the shared
  `CardiacClock`. It does not consume a waveform sample, reconstruct a 12-lead
  signal, solve an activation field, or estimate a physical conduction velocity.
- The heart shader's activation band also follows the normalized cardiac phase.
  Its position and glow are visual timing effects. The frontend does not turn
  the backend `electrical_wave_speed` field into a measured propagation speed.

The correct label for this layer is therefore:

> `Simulated electrical visualization · shared cardiac clock · visualization-only`

It remains permissible to show the nodes and moving activation cue when ECG
data is missing, provided the missing-data label is visible and the animation is
not described as the patient's ECG.

## M7 split-heart policy

The split view consumes one valid persisted M6 pair. Its two renderers receive
separate baseline and counterfactual states, but their ECG/electrical displays
remain bounded projections:

1. `comparisonVisualization` copies the existing visualization template and
   replaces the side's heart rate, cycle duration, scalar hemodynamic readouts,
   and EF-related fields. Its RR value is `60000 / heart_rate_bpm` when a valid
   heart rate is available.
2. It carries the template electrophysiology context and overrides timing RR;
   it does not create a scenario ECG waveform, new QRS/QTc morphology, or a
   new conduction map.
3. The comparison clock controls the rendered phase. `Phase locked` means both
   views share the same normalized visual phase while their rate labels remain
   distinct. `True rate` advances each side at its modeled heart rate and may
   let the phases drift. Neither mode is an ECG replay mode.
4. The current signal-context cards are allowed to say `Simulated timing
   context; no measured waveform inferred` and `Educational signal context
   only`. Keep those qualifications adjacent to the side-specific label.
5. The split view may show a side's persisted rhythm label as context, but must
   retain its source label. A counterfactual rhythm label copied from a template
   is not evidence that the scenario generated that rhythm.

Recommended side labels:

```text
Baseline · M7 baseline paired state
Counterfactual · M7 counterfactual paired state
Simulated timing context · HR-derived RR · no measured waveform inferred
HYPOTHETICAL SIMULATION · educational projection only
```

The M7 comparison must not show an ECG delta merely because heart rate or RR
changed. A signal delta requires two explicitly sourced signal records and a
deterministic comparison contract; the current paired visual projection does
not provide that contract.

## Must not be fabricated

The following claims or visuals are outside the current evidence boundary:

- A raw ECG trace, P/QRS/T morphology, ST segment, rhythm strip, or 12-lead
  reconstruction generated from HR, RR, QRS, QTc, a rhythm label, or the 3D
  activation animation.
- A patient-specific conduction velocity, activation-time map, vectorcardiogram,
  action-potential trace, or electrical propagation field from fixed node phases,
  proxy coordinates, `wave_speed`, or shader motion.
- A counterfactual ECG waveform or a claim that the scenario changed conduction,
  repolarization, rhythm, or arrhythmia behavior when only HR-derived timing was
  projected.
- Diagnostic conclusions such as arrhythmia, ischemia, infarction, conduction
  disease, or repolarization disease from a descriptor, QRS/QTc threshold,
  instability score, or electrical color/animation.
- A causal claim that the electrical layer explains a regional lesion, scar,
  EF, contractility, or hemodynamic change. The electrical overlay and tissue
  overlay are separate educational layers.
- A measured-data label for synthetic replay, a report-only descriptor, a prior,
  or an M7 counterfactual projection. Synthetic snapshots remain visibly
  `REPLAY`/`DEMO STREAM` where applicable.
- A waveform or numeric feature at a cursor where the selected snapshot has no
  supported ECG evidence. Use `missing`, `unknown`, or `unavailable`.

## Labeling checklist for reviewers

Before accepting an ECG/electrical surface, verify:

- The visible signal kind is one of `measured`, `extracted`, `simulated`, or
  `missing`, with backend-specific `reported`, `waveform_estimated`, or
  `unknown` detail retained where relevant.
- A waveform preview includes lead, sampling rate, method, and confidence; if
  those are unavailable, it is not presented as a waveform recording.
- Every 3D activation view says `simulated`, `visualization-only`, or equivalent
  language near the visual or in its inspector.
- Baseline and counterfactual labels identify the pair side and preserve
  provenance; copied template fields are not described as newly simulated ECG
  observations.
- Missing or insufficient data stays missing. No fallback trace is generated
  for visual completeness.
- No UI copy converts an ECG descriptor or proxy score into diagnosis,
  treatment guidance, or a claim of patient-specific electrical mechanics.

## Source references

- Backend source and safety labels: [`python/hearttwin/agents/electrophysiology_agent.py`](../../python/hearttwin/agents/electrophysiology_agent.py)
- Deterministic waveform feature rules: [`python/hearttwin/tools/ecg_features.py`](../../python/hearttwin/tools/ecg_features.py)
- Canonical electrophysiology state: [`python/hearttwin/schemas.py`](../../python/hearttwin/schemas.py)
- ECG timeline type contract: [`web/lib/twin/ecg/index.ts`](../../web/lib/twin/ecg/index.ts)
- Temporal ECG projection: [`web/lib/twin/integration/context.tsx`](../../web/lib/twin/integration/context.tsx)
- 3D electrical nodes and fixed visual phases: [`web/components/heart/electrical/model.ts`](../../web/components/heart/electrical/model.ts)
- 3D electrical renderer: [`web/components/heart/electrical/ElectricalLayer.tsx`](../../web/components/heart/electrical/ElectricalLayer.tsx)
- Heart activation shader and shared clock usage: [`web/components/heart/HeartScene.tsx`](../../web/components/heart/HeartScene.tsx)
- M7 paired visual projection: [`web/lib/twin/comparison/visualization.ts`](../../web/lib/twin/comparison/visualization.ts)
- M7 split-heart signal cards: [`web/components/twin/comparison/SplitHeartComparison.tsx`](../../web/components/twin/comparison/SplitHeartComparison.tsx)
- Existing ECG safety and interpolation policy: [`docs/hackathon/M3_INTERPOLATION_POLICY.md`](./M3_INTERPOLATION_POLICY.md), [`docs/hackathon/M4_PHYSIOLOGY_AUDIT.md`](./M4_PHYSIOLOGY_AUDIT.md)
