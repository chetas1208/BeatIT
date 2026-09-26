# M4 Physiology Formula Audit

**Status:** read-only audit; no Python implementation changes made  
**Audit date:** 2026-09-26  
**Purpose:** establish the deterministic physiology contract before the M4 causal
scenario layer is implemented.

## 1. Executive findings

BeatIT has two distinct numerical layers:

1. **Evidence-derived cardiac metrics** in `tools/cardiac_state.py` and the
   state-builder agent. These are pure, deterministic calculations from measured
   inputs and are the canonical values for SV, EF, CO, MAP, RR, QTc, BSA, and
   the simplified indices.
2. **Educational simulation outputs** in `tools/hemodynamics.py`,
   `tools/recovery_sim.py`, `tools/ecg_features.py`, and `tools/ct_volumetry.py`.
   These are deterministic approximations or signal/volume-processing proxies;
   they are not calibrated clinical models.

The deterministic core does not call an LLM. The model layer may narrate or
explain already-computed values, but must not calculate or overwrite them.

### Findings that affect M4

- `simulate_pv_loop` and `simulate_cardiac_cycle` accept `afterload_index`, but
  the current numerical equations do not use that argument. The hemodynamics
  agent applies afterload to the derived index and passes it to the visualization
  simulation, but it is not a causal input to the pressure/volume equations.
- `simulate_recovery` updates several latent indices, but EF and CO change
  directly through ESV and heart rate. Among inflammation, oxygen delivery,
  stiffness, and arrhythmia, only stiffness affects ESV through the current
  volume-shift equation; contractility and afterload also affect ESV.
- Recovery uncertainty uses seeded Gaussian noise for the displayed bands only;
  the noise does not alter the trajectory state.
- ECG rhythm labels, arrhythmia instability, conduction delay, and CT findings
  are explicitly educational proxies. They must not be promoted to diagnoses or
  chamber-level claims.
- The PV loop and cardiac-cycle implementations clamp invalid ESV values for
  simulation, while the canonical `cardiac_state` functions reject invalid
  volume ordering. M4 must preserve that distinction and surface the warning.

## 2. Canonical evidence-derived formulas

Source: [`python/hearttwin/tools/cardiac_state.py`](../../python/hearttwin/tools/cardiac_state.py).
Inputs are represented by `MeasuredValue` with value, unit, source, confidence,
and optional provenance in [`python/hearttwin/schemas.py`](../../python/hearttwin/schemas.py:84-91).

| Function / source | Inputs and units | Formula | Output and units | Assumptions and guards |
|---|---|---|---|---|
| `compute_stroke_volume` (`:13-17`) | EDV, ESV; mL | `SV = EDV - ESV` | Stroke volume; mL | Requires `ESV < EDV`; equality and reversal raise `ValueError`. |
| `compute_ejection_fraction` (`:20-25`) | EDV, ESV; mL | `EF = (SV / EDV) × 100` | Ejection fraction; % | Requires `EDV > 0` and valid volume ordering. |
| `compute_cardiac_output` (`:28-34`) | HR; bpm, SV; mL | `CO = HR × SV / 1000` | Cardiac output; L/min | `/1000` converts mL/min to L/min. HR and SV must be positive. |
| `compute_map` (`:37-41`) | SBP, DBP; mmHg | `MAP = DBP + (SBP - DBP) / 3` | Mean arterial pressure; mmHg | Assumes the conventional one-third pulse-pressure approximation; requires `DBP < SBP`. |
| `compute_afterload_index` (`:44-53`) | MAP; mmHg, CO; L/min | `(MAP / 93) / (CO / 5.0)` | Dimensionless index | Simplified normalized proxy; 93 mmHg and 5 L/min are fixed typical reference values. |
| `compute_svr_index` (`:56-61`) | MAP; mmHg, CO; L/min, optional CVP; mmHg | `((MAP - CVP) / CO) / 17.6` | Dimensionless index | Simplified normalized SVR proxy; CVP defaults to 5 mmHg; 17.6 is a fixed normalization constant. |
| `compute_preload_index` (`:64-68`) | EDV; mL | `EDV / 130` | Dimensionless index | Simplified preload proxy normalized to 130 mL; EDV must be positive. |
| `compute_contractility_index` (`:71-74`) | EF; %, afterload index; dimensionless | `(EF / 60) / max(afterload, 0.1)` | Dimensionless index | EF-derived, afterload-adjusted proxy; denominator floor avoids division by zero. |
| `compute_bsa_mosteller` (`:77-81`) | Height; cm, weight; kg | `BSA = sqrt(height × weight / 3600)` | Body surface area; m² | Mosteller convention; both inputs must be positive. |
| `compute_qtc_bazett` (`:84-89`) | QT; ms, RR; ms | `QTc = QT / sqrt(RR / 1000)` | Corrected QT; ms | Bazett correction; RR is converted to seconds and must be positive. |
| `compute_rr_from_hr` (`:92-96`) | HR; bpm | `RR = 60000 / HR` | RR interval; ms | One minute is 60,000 ms; HR must be positive. |
| `check_ef_consistency` (`:99-116`) | Reported EF; %, EDV/ESV; mL | `abs(reported EF - computed EF)` | Boolean plus message; tolerance in percentage points | Missing volumes return “cannot verify” and `True`; default tolerance is 5 percentage points. |
| `compute_filling_pressure_index` (`:119-122`) | EDV; mL, stiffness index; dimensionless | `(EDV / 130) × stiffness` | Dimensionless proxy | Simplified filling-pressure proxy; no explicit input guard is applied in this function. |
| `compute_arterial_compliance_index` (`:125-130`) | SV; mL, pulse pressure; mmHg | `(SV / pulse pressure) / 2` | Dimensionless index | Simplified compliance proxy normalized to 80 mL / 40 mmHg; pulse pressure must be positive. |

`validate_bounds` (`cardiac_state.py:133-149`) does not calculate physiology. It
looks up configured ranges and returns warnings. The current bounds are in
[`python/hearttwin/data/parameter_bounds.json`](../../python/hearttwin/data/parameter_bounds.json)
and are validation policy, not formula constants.

### Evidence derivation policy

The state builder derives SV/EF only when real EDV and ESV evidence is present
and ordered, derives CO only from real HR and derived/real SV, derives MAP only
from real SBP/DBP, and does not overwrite a reported EF. See
[`python/hearttwin/agents/state_builder_agent.py`](../../python/hearttwin/agents/state_builder_agent.py:385-439).
RR, QTc, and BSA follow the same provenance-aware policy at `:457-484` and
`:569-575`. A default prior must not be relabeled as observed evidence.

## 3. Operating-environment modifiers

Source: [`python/hearttwin/agents/hemodynamics_agent.py`](../../python/hearttwin/agents/hemodynamics_agent.py:86-188).
The operating environment is bounded before use. Current bounds include METs
`[0, 20]`, hydration and sleep `[0, 2]`, stress `[0, 5]`, temperature
`[-10, 50]` °C, altitude `[0, 5500]` m, oxygen fraction `[0.10, 0.30]`, and
time step `[0.1, 100]` ms (`:86-96`). Out-of-range values are clamped with a
warning.

| Modifier | Current equation | Output / units | Assumptions |
|---|---|---|---|
| Activity HR | `1 + max(0, MET - 1) × 0.08` | HR multiplier; dimensionless | Only activity above 1 MET raises this modifier. |
| Stress HR | `1 + max(0, stress - 1) × 0.10` | HR multiplier; dimensionless | Stress below 1 has no effect in this term. |
| Stress afterload | `1 + max(0, stress - 1) × 0.15` | Afterload multiplier; dimensionless | Simplified catecholamine proxy. |
| Temperature HR | `1 + min(abs(temp - 22) × 0.007, 0.20)` | HR multiplier; dimensionless | Symmetric deviation from 22 °C; capped at +20%. |
| Hydration preload | `clamp(0.7 + 0.3 × min(hydration, 2), 0.7, 1.3)` | Preload multiplier; dimensionless | Hydration affects preload only through this proxy. |
| Sleep contractility | `clamp(0.8 + 0.2 × min(sleep, 1), 0.8, 1.0)` | Contractility multiplier; dimensionless | Sleep above 1 does not increase contractility. |
| Altitude oxygen | `max(0.70, 1 - altitude × 0.000055)` | O₂-delivery multiplier; dimensionless | Linear 5.5% per 1000 m approximation with 0.70 floor. |
| Oxygen fraction | `oxygen_fraction / 0.21` | O₂-delivery multiplier; dimensionless | Relative to 21% reference; no independent saturation model. |
| Medication profile | Supplied `heart_rate_multiplier`, `contractility_multiplier`, and `afterload_multiplier` | Dimensionless multipliers | Missing keys default to 1.0. |

The combined modifiers are products of their relevant terms (`:168-172`).
Tissue contractility then applies `max(0.3, 1 - scar × 1.5)` and multiplies it
by `max(0.5, 1 - inflammation × 0.3)` (`hemodynamics_agent.py:441-447`).
The resulting contractility and afterload modifiers are clamped before use.

Operating-mode overrides are applied after the base HR modifier
(`hemodynamics_agent.py:454-463`): mild activity multiplies HR by 1.2 and SBP
by 1.1; stress multiplies HR by 1.5 and SBP by 1.2; recovery multiplies HR by
0.9 with a 40 bpm floor. These are simulation controls, not clinical response
models.

## 4. Pressure-volume loop and cardiac-cycle simulation

Source: [`python/hearttwin/tools/hemodynamics.py`](../../python/hearttwin/tools/hemodynamics.py).
Both generators are deterministic educational approximations. The returned
payload labels the model `simplified_time_varying_elastance` and
`educational simulation` (`:214-226`).

### 4.1 Shared inputs and guards

Inputs are EDV/ESV (mL), HR (bpm), SBP/DBP (mmHg), contractility index and
afterload index (dimensionless), plus sample count or time step. If `ESV >= EDV`,
both simulation paths replace ESV with `0.4 × EDV` and append a warning
(`hemodynamics.py:81-86` and `:341-344`). The canonical formula functions do not
do this; they reject the state.

### 4.2 PV-loop equations

For `simulate_pv_loop` (`:64-160`):

- `cycle_ms = 60000 / HR`.
- Timing fractions: systole ends at `0.40 × cycle_ms`; isovolumetric contraction
  lasts `0.07 × cycle_ms`; isovolumetric relaxation lasts `0.08 × cycle_ms`.
- End-diastolic pressure:
  `EDP = clamp(8 + (EDV - 130) × 0.05, 2, 30)` mmHg.
- Effective maximum elastance:
  `Emax = max(0.5, (SBP / (SV × 0.8)) × contractility_index)` with the
  implementation’s resulting pressure scale treated as mmHg/mL.
- Unstressed volume: `V0 = 0.85 × ESV` mL.
- Normalized elastance `E_n(t)` (`:43-61`) is
  `sin(pi × t_norm / 0.7)²` for `t_norm ≤ 0.70` (the first `≤0.35` branch
  currently has the same equation), and zero after 0.70. `t_norm` is clamped
  to `[0, 1]`.
- Isovolumetric contraction: `V = EDV`; `P = EDP + 0.3 × E_n × Emax × (V - V0)`.
- Ejection: `f = (t - t_iso_contract) / (t_sys_end - t_iso_relax - t_iso_contract)`;
  `V = EDV - SV × sin(pi × f / 2)²`; `P = max(DBP, E_n × Emax × (V - V0))`.
- Isovolumetric relaxation: `V = ESV`; `P = 0.5 × E_n × Emax × (V - V0) + 0.5 × DBP`.
- Filling: `f = (t - t_sys_end) / (cycle_ms - t_sys_end)`;
  `V = ESV + SV × f`; `r = min(1, (t - t_sys_end)/(2 × t_iso_relax))`;
  `P = max(0, EDP × f + (1-r) × DBP × 0.2)`.
- Volume and pressure samples are rounded to two decimal places before area
  calculation. `n_points` defaults to 200.

The `afterload_index` argument is accepted and forwarded by callers, but is not
used in these equations. This is a documented current limitation, not an
implicit causal relationship.

### 4.3 PV area and stroke work

`_compute_pv_loop_area` (`:163-171`) applies the closed polygon shoelace sum:

```text
area = abs(sum(V[i] × P[i+1] - V[i+1] × P[i])) / 2
```

Output is in mmHg·mL. Stroke work uses:
`area × 1e-6 × 133.322`, output in joules. The generated chart payload also
exposes `loop_area_index = area / 4000`, a dimensionless display normalization
(`:190-227`).

### 4.4 Cardiac-cycle equations

`simulate_cardiac_cycle` (`:328-418`) uses the same cycle timing, EDP, Emax,
unstressed volume, and ejection-volume shape, with these implementation details:

- `n_steps = max(50, int(cycle_ms / time_step_ms))`.
- During contraction, pressure linearly interpolates from EDP to
  `Emax × (EDV - V0)`; flow is zero.
- During ejection, flow is
  `(previous_volume - current_volume) / (time_step_ms / 1000)` in mL/s and is
  clamped at zero for output.
- During relaxation, volume is ESV and pressure is
  `Emax × (1 - relax_fraction) × (ESV - V0) × 0.5 + DBP`.
- During filling, volume is the linear ESV-to-EDV interpolation and pressure is
  `max(0, EDP × fill_fraction)`.
- Cardiac output is recomputed as `HR × SV / 1000` L/min. Arrays are rounded to
  two decimals and cycle duration to one decimal.

The cycle’s `afterload_index` is likewise passed to `simulate_pv_loop` only and
does not enter the cycle equations. Phase labels in
`generate_cardiac_cycle` are descriptive simulation labels, not measured valve
events.

### 4.5 Oxygen demand and visualization mappings

`compute_oxygen_demand_index` (`hemodynamics.py:174-187`) computes:

```text
raw = (HR / 70) × max(0, contractility) × max(0, afterload) × max(0, METs)
index = clamp(raw, 0, 5), rounded to four decimals
```

This is a dimensionless MVO2 proxy, not oxygen consumption.

`generate_3d_visual_payload` (`:284-325`) maps numerical indices to visual
controls. For example, beat interval is `60000 / max(HR, 1)`, particle density
is `clamp(oxygen_delivery × 1.1, 0, 1)`, stress intensity is
`clamp(0.6 × afterload + 0.4 × inflammation, 0, 1)`, and beat amplitude,
contractility, preload, scar, and wave speed are clamped display values. These
are frontend mappings and must not be treated as additional physiology.

## 5. Recovery trajectory simulation

Source: [`python/hearttwin/tools/recovery_sim.py`](../../python/hearttwin/tools/recovery_sim.py:67-268).
The result is explicitly labeled “bounded educational simulation, not a
treatment recommendation” (`:39-52`).

### Per-day outputs

For every day, with current EDV and ESV:

- `SV = max(5, EDV - ESV)` mL.
- `EF = SV / max(EDV, 1) × 100` %.
- `CO = HR × SV / 1000` L/min.
- `noise_frac = Gaussian(0, 0.025)` from a local seeded RNG.
- `uncertainty_range = uncertainty_penalty_weight × 0.10 + abs(noise_frac)`.
- `uncertainty_low = CO × (1 - uncertainty_range)` and
  `uncertainty_high = CO × (1 + uncertainty_range)` L/min.

The random term changes only uncertainty bands. It does not change EDV, ESV,
HR, EF, or CO. A fixed `random_seed` makes the bands reproducible.

### Day-to-day state updates

At each transition, every delta is first limited to
`[-max_safe_parameter_shift, +max_safe_parameter_shift]` and then bounded:

| State | Update | Bound / units |
|---|---|---|
| Inflammation | `floor + (current - floor) × exp(-decay_rate)`, with floor 0 | `[0, 1.5]`, dimensionless |
| Contractility | `current + clamp(delta/day)` | `[0, 1.5]`, dimensionless |
| Afterload | `current + clamp(delta/day)` | `[0, 2.0]`, dimensionless |
| Preload | `current + clamp(delta/day)` | `[0, 1.5]`, dimensionless |
| Oxygen delivery | `current + clamp(delta/day)` | `[0, 1.5]`, dimensionless |
| Stiffness | `current + clamp(delta/day)` | `[0, 2.0]`, dimensionless |
| Scar | `current + clamp(-scar_remodeling_rate, -0.01, 0)` | `[0, 0.6]`, dimensionless fraction |
| Arrhythmia instability | `current + clamp(-stability_delta)` | `[0, 1.0]`, dimensionless |
| Heart rate | `current + (target - current) × adaptation_rate` | `[30, 200]`, bpm; target is 60 for `load_reduction`, otherwise baseline HR |

The ESV shift is:

```text
contractility_effect = (current_contractility - baseline_contractility) × 15
afterload_effect      = (baseline_afterload - current_afterload) × 10
stiffness_effect      = (baseline_stiffness - current_stiffness) × 8
volume_shift          = sum of the three effects
ESV_next = clamp(ESV_current - clamp(volume_shift × 0.5, -5, 5),
                 5, EDV × 0.9)
```

If ESV still reaches EDV, it is clamped to `0.4 × EDV` with a warning. EDV is
not updated by this simulator. The current implementation therefore does not
propagate oxygen delivery, inflammation, or arrhythmia directly into EF/CO;
they remain trajectory metadata and summary signals.

## 6. ECG signal-derived formulas and proxies

Source: [`python/hearttwin/tools/ecg_features.py`](../../python/hearttwin/tools/ecg_features.py).
This is a lightweight Pan-Tompkins-inspired educational pipeline, not a
clinical ECG interpreter.

| Stage | Formula / rule | Output and units | Assumptions |
|---|---|---|---|
| Moving-average filter (`:33-50`) | `window_low = int(fs / 15)`, `window_high = int(fs / 5)`; output is short-window average minus long-window average | Filtered waveform; signal units | Approximate bandpass; edge windows are shortened. |
| Derivative (`:53-58`) | Interior sample `(x[i+1] - x[i-1]) / 2`; endpoints zero | Signal derivative; signal units/sample | Sampling interval is not included in the derivative scale. |
| Squaring and integration (`:61-73`) | `x²`, then trailing moving average over `int(0.15 × fs)` samples | Integrated energy-like signal; squared signal units | 150 ms window. |
| Peak threshold (`:89-117`) | Threshold `0.35 × max(integrated)`; local maximum plus refractory interval | R-peak indices; samples | Default fs 500 Hz, refractory 200 ms; approximate confidence only. |
| RR interval (`:127-135`) | `(peak[i] - peak[i-1]) / fs × 1000` | RR; ms | Requires at least two peaks. |
| Heart rate (`:210-216`) | `60000 / mean RR` | HR; bpm | Derived from detected peaks. |
| QTc (`:138-143`) | Bazett: `QT / sqrt(mean RR / 1000)` | QTc; ms | Only when QT is supplied. |
| Rhythm descriptor (`:146-160`) | `HR = 60000 / max(mean RR, 100)`; variability ratio `RR std / mean RR`; irregular if ratio > 0.25, else HR thresholds 50/100 | Simulation-safe string | Labels intentionally say “simulated … pattern,” not diagnosis. |
| Instability (`:163-175`) | `RMSSD = sqrt(sum((RR[i]-RR[i-1])²)/(n-1))`; score `min(1, RMSSD / mean RR)` | Dimensionless `[0, 1]` | Higher means more interval irregularity in this proxy. |
| Conduction delay (`:222-225`) | `0` at QRS ≤ 120 ms; otherwise `min(1, (QRS - 120)/80)` | Dimensionless `[0, 1]` | Simplified display score. |

With fewer than two detected peaks, waveform-derived RR/HR/QTc and rhythm
estimation are unavailable and the function returns a warning rather than
inventing them (`:191-208`).

## 7. CT label-map volumetry

Source: [`python/hearttwin/tools/ct_volumetry.py`](../../python/hearttwin/tools/ct_volumetry.py:131-166).
For each non-background segmentation label:

```text
voxel_volume_mm3 = spacing_x_mm × spacing_y_mm × spacing_z_mm
volume_ml = voxel_count × voxel_volume_mm3 / 1000
```

The output is per-label volume in mL. NIfTI labels are rounded/cast to integer
IDs before counting (`:120-125`). The configured VISTA-3D label 115 is one whole
heart label; it is not a four-chamber segmentation. The only abnormality output
is a global whole-heart volumetric proxy with educational reference values
(`normal_max=900`, `mild=1000`, `moderate=1150`, `severe=1350` mL) from
[`python/hearttwin/data/ct_reference_ranges.json`](../../python/hearttwin/data/ct_reference_ranges.json).

The aorta and other labels are presence/context observations. The code does not
derive chamber EF, regional wall motion, myocardial scar, or a diagnosis from
this mask (`ct_volumetry.py:169-261`).

### Educational finding thresholds

The separate findings layer applies display bands; it does not calculate new
physiology. In [`python/hearttwin/tools/cardiac_findings.py`](../../python/hearttwin/tools/cardiac_findings.py:146-243):

- EF `<30%`, `<40%`, and `<50%` map to severe, moderate, and mild educational
  bands respectively; EF `≥50%` emits no reduced-EF finding.
- Scar fraction `>0`, `≥0.10`, and `≥0.25` map to mild, moderate, and severe
  display bands (`:117-126`).
- QRS `>120 ms` emits a conduction observation; `≥150 ms` changes its display
  band from mild to moderate.
- QTc `>460 ms` emits a repolarization observation; `≥500 ms` changes its
  display band from mild to moderate.

These thresholds are presentation policy over supplied metrics. The layer
retains an educational disclaimer and must not be treated as a diagnostic rule.

## 8. Cross-layer data contract for M4

The canonical state separates measurements, electrophysiology, hemodynamics,
tissue state, operating environment, simulation configuration, and provenance
in `CardiacTwinState` (`python/hearttwin/schemas.py:248-264`). M4 scenario code
must preserve these invariants:

1. **Observed state is immutable.** Fork a scenario from a snapshot; do not
   write hypothetical values into the observed state.
2. **Formulas remain deterministic.** Scenario propagation may call existing
   pure functions with explicit inputs, but must not duplicate or silently
   alter their equations.
3. **Provenance survives derivation.** Derived fields remain marked as derived;
   priors, user input, file extraction, and simulation remain distinguishable.
4. **Units stay explicit.** Use the field units in `MeasuredValue` and the
   tables above; do not compare raw numbers across mL, L/min, mmHg, ms, %, and
   dimensionless indices.
5. **Warnings remain attached.** Invalid volume ordering, pressure ordering,
   clamping, missing inputs, or proxy limitations must be visible in the
   scenario trace/report.
6. **No model arithmetic.** Language models can explain computed deltas and
   provenance but cannot produce authoritative EF, CO, MAP, PV area, recovery
   trajectories, or units.

## 9. Explicit do-not-change findings

This audit is not authorization to alter formulas. Until the lead approves a
separate model change with new golden tests and an updated audit:

- Do not change the formulas or constants in `tools/cardiac_state.py`.
- Do not replace the evidence/provenance gates in `state_builder_agent.py` with
  prior-based derivation.
- Do not “fix” PV-loop or cardiac-cycle behavior by changing the equations as
  part of M4 scenario work. Preserve the current educational model and its
  warnings.
- Do not assume `afterload_index` affects PV pressure or volume until a dedicated
  causal-model decision explicitly changes and tests that contract.
- Do not feed recovery uncertainty noise into the physiological state.
- Do not turn CT whole-heart volume into chamber-level physiology.
- Do not turn ECG descriptors or instability scores into diagnoses.
- Do not treat visualization mappings, normalization constants, or indices as
  measured clinical quantities.
- Do not remove the educational/safety labels from simulated outputs.
- Do not ask a model provider to calculate any of the formulas documented here.

Existing formula coverage includes the golden tests in
[`python/hearttwin/tests/test_cardiac_formulas_golden.py`](../../python/hearttwin/tests/test_cardiac_formulas_golden.py),
[`test_cardiac_formulas.py`](../../python/hearttwin/tests/test_cardiac_formulas.py),
[`test_hemodynamics.py`](../../python/hearttwin/tests/test_hemodynamics.py),
and [`test_recovery_sim.py`](../../python/hearttwin/tests/test_recovery_sim.py).
