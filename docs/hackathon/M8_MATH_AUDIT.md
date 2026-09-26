# M8 Mathematical Architecture Audit

Status: **read-only audit and method boundary**
Role: **M8 mathematical architecture auditor**
Date: 2026-09-26

This document defines the defensible Tier-1 mathematical method for M8. It
does not implement sensitivity, uncertainty attribution, or evidence ranking.
It is intentionally constrained by the deterministic M5.5 ensemble and the
paired M6 Shadow Trial contracts that exist in this repository.

## Executive finding

BeatIT has enough structure for a transparent **local finite-perturbation
sensitivity analysis**:

```text
persisted parameter sample
        + bounded perturbation
        -> canonical deterministic evaluator
        -> output response or paired Shadow Trial effect response
```

The result can support target-specific local sensitivity and a clearly labeled
**uncertainty-impact heuristic**. It cannot currently support a claim of
global variance attribution, Sobol indices, Shapley effects, posterior
uncertainty reduction, or expected information gain.

The recommended M8 default is therefore:

1. evaluate each parameter perturbation with the canonical evaluator;
2. report raw derivatives with their natural units;
3. report a separately normalized, dimensionless response for comparison;
4. combine that response with a normalized empirical parameter spread;
5. rank evidence types using explicit constraint weights and call the result
   an **Evidence Priority Score**, never information gain.

## Evidence inspected

The audit inspected the implementation rather than treating prior milestone
documents as implementation proof:

| Evidence | Relevant authority |
|---|---|
| Parameter bounds and distributions | `python/hearttwin/ensemble.py:22-74` |
| Sample, projection-base, and ensemble lineage | `python/hearttwin/ensemble.py:188-323` |
| Baseline extraction and deterministic evaluator | `python/hearttwin/ensemble.py:332-375` |
| Seeded ensemble generation and output summaries | `python/hearttwin/ensemble.py:416-468` |
| Primitive cardiac formulas and units | `python/hearttwin/tools/cardiac_state.py:12-89` |
| M6 paired scenario application and canonical deltas | `python/hearttwin/shadow_trial_engine.py:114-144,169-244` |
| M6 effect units and descriptive statistics | `python/hearttwin/shadow_trial_contracts.py:20-58`, `python/hearttwin/shadow_trial_metrics.py:20-66` |
| Existing uncertainty boundary | `docs/hackathon/M5_UNCERTAINTY_MODEL.md:3-17` |
| Existing distribution boundary | `docs/hackathon/M5_PARAMETER_DISTRIBUTIONS.md:3-14` |
| Existing paired-effect boundary | `docs/hackathon/M6_EFFECT_METRICS.md:3-25` |

## What is uncertain now

### Input parameters

The active ensemble has exactly five bounded deterministic input proxies. Their
model units and allowed evaluator domains are:

| Parameter ID | Meaning in the model | Unit | Evaluator bounds |
|---|---|---:|---:|
| `heart_rate_bpm` | heart rate input | `bpm` | `[30, 200]` |
| `preload_index` | normalized preload proxy | `index` | `[0, 1.5]` |
| `afterload_index` | normalized afterload proxy | `index` | `[0, 2]` |
| `contractility_index` | normalized contractility proxy | `index` | `[0, 1.5]` |
| `systemic_vascular_resistance_index` | normalized SVR proxy | `index` | `[0, 2]` |

The request contract supports fixed, normal, lognormal, uniform, and empirical
families. A normal or lognormal draw may be rejected when it falls outside its
declared bounds; the ensemble does not silently turn that rejection into a
clipped accepted value. The current provenance explicitly states that inputs
are sampled independently because no validated joint correlation model is
available. Therefore any M8 result must preserve the following distinction:

- **parameter spread**: spread of the accepted sampled proxy values;
- **measurement uncertainty**: only a quantitative measurement error actually
  supplied by evidence;
- **prior uncertainty**: bounded assumptions used when evidence is absent;
- **missing evidence**: absence, not a fabricated numeric distribution.

`MeasuredValue.confidence` is a provenance/quality score, not a probability,
standard deviation, coverage level, or posterior confidence. This is the M5
boundary and must remain unchanged.

### Outputs and effects

The ensemble response publishes descriptive distributions for:

| Metric ID | Unit |
|---|---:|
| `ejection_fraction_pct` | `%` for values; M6 delta is percentage points |
| `stroke_volume_ml` | `mL` |
| `cardiac_output_l_min` | `L/min` |
| `heart_rate_bpm` | `bpm` |

The persisted sample evaluator also returns `edv`, `esv`, and `map`; M6 maps
these to `edv_ml`, `esv_ml`, and `map_mmhg` when available. M6 effects are always
the raw same-pair subtraction:

```text
effect_m = scenario_value_m - baseline_value_m
```

Near-zero tolerances classify effects for display only. They do not round or
alter the underlying deltas.

## Numerical authority and lineage rules

Tier 1 must use the accepted `EnsembleSample` as the baseline authority:

1. use `sample.parameters` as the parameter vector;
2. use `sample.projection_base` as the exact deterministic base;
3. evaluate the baseline and perturbations through the canonical evaluator;
4. never re-sample, infer, or re-project from the already projected UI state;
5. exclude invalid samples and perturbations that do not produce a valid finite
   output, while retaining an explicit unavailable reason;
6. carry ensemble ID, sample ID, seed, origin snapshot, distribution version,
   physiology version, prior version, and sensitivity configuration into
   provenance.

This is essential because M6 deliberately preserves the persisted baseline
outputs and applies a scenario to the corresponding sample's
`projection_base`. A sensitivity engine that starts from `sample.state` can
apply sampled inputs twice and produce a plausible-looking but invalid result.

## Tier-1 finite-perturbation method

### Target definition

Sensitivity is always target-specific. A target is a tuple:

```text
(sample_id, parameter_id, metric_id, target_kind)
```

`target_kind` is one of:

- `baseline_output`: the canonical output `Y_m(theta)`;
- `shadow_effect`: the paired effect `E_m(theta)`, where the scenario is held
  fixed and `E_m = Y_m(theta_scenario) - Y_m(theta_baseline)`.

There is no single universal parameter ranking. A parameter can be influential
for stroke volume and weak for heart rate, while the ranking for a Shadow Trial
effect can differ again.

### Perturbation size and domain handling

For parameter `theta_i` with declared evaluator bounds `[L_i, U_i]`, define:

```text
R_i = U_i - L_i
Q_i = max(abs(theta_i), 0.5 * R_i)
h0_i = 0.05 * Q_i
h_i = min(h0_i, 0.05 * R_i)
```

`h_i` is in the parameter's native unit. The five-percent factor is a
versioned Tier-1 default, not a learned quantity. It is large enough to avoid
floating-point noise and small enough to describe a local response for this
low-dimensional evaluator. A future implementation may expose the factor as a
configuration value, but it must be recorded in provenance and not changed
silently between runs.

Use a central difference when both `theta_i - h_i` and `theta_i + h_i` are
inside `[L_i, U_i]`. Near a bound, use the available one-sided difference:

```text
central:  (Y(theta_i + h_i) - Y(theta_i - h_i)) / (2 * h_i)
forward:  (Y(theta_i + h_i) - Y(theta_i)) / h_i
backward: (Y(theta_i) - Y(theta_i - h_i)) / h_i
```

If the requested step cannot fit on either side, or either canonical
evaluation is invalid/non-finite, return `unavailable` for that target. Do not
shrink the step repeatedly without recording the resulting method and step.

The evaluator's own floors and ceilings (`EDV`, `ESV`, and `MAP`) remain the
model authority. A derivative of zero at an active model clamp is a
**boundary-local response**, not evidence that the parameter has no biological
influence. The result should carry a boundary/clamp note whenever the
perturbed outputs indicate such a regime.

### Raw local sensitivity

For output metric `m`, let `D_i,m` be the finite difference above. Its unit is
the output unit divided by the input unit:

```text
D_i,m = output_unit_m / parameter_unit_i
```

Examples include `mL/index`, `L/min/bpm`, and `percentage_points/index`.
Raw derivatives must be retained because they are interpretable and auditable.
They must not be ranked directly across mixed units.

### Dimensionless comparison response

For cross-parameter display, define a reference scale for each parameter and
metric:

```text
P_i = max(abs(theta_i), 0.5 * R_i)
Y_m = max(abs(Y_m(theta)), y_floor_m)
S_i,m = D_i,m * P_i / Y_m
```

`S_i,m` is a dimensionless normalized local response. It is elasticity-like,
but must not be called a mathematical elasticity when `theta_i` or `Y_m` is
near zero. `y_floor_m` prevents division by a small or zero output and is a
presentation scale, not a physiological threshold. The default scales are:

| Metric family | `y_floor_m` |
|---|---:|
| EF percentage points | `1` percentage point |
| SV, EDV, ESV | `1 mL` |
| CO | `0.1 L/min` |
| HR | `1 bpm` |
| MAP | `1 mmHg` |

The configured scales, perturbation factor, difference direction, raw values,
and boundary flags must be stored with every result. If a different scale is
needed, it is a new sensitivity configuration version, not an undocumented UI
choice.

### Shadow-Trial effect sensitivity

For a selected M6 scenario, calculate sensitivity of the effect itself rather
than confusing it with sensitivity of the scenario output:

```text
E_m(theta) = Y_m(theta; scenario) - Y_m(theta; baseline)
```

For a parameter not directly changed by the scenario, perturb the same
parameter in both baseline and scenario vectors while keeping the scenario
definition fixed. For a parameter directly changed by the scenario, perturb
the baseline value but hold the scenario's absolute target value fixed. This
answers “how does the modeled effect change with the uncertain baseline?” and
does not silently change the intervention being analyzed.

The same finite-difference and unit normalization rules apply to `E_m`. A
scenario effect sensitivity is not a causal estimate, treatment effect, or
clinical response estimate; it is local variation of a deterministic
counterfactual projection under the declared scenario.

## Distribution-aware uncertainty magnitude

For each parameter, calculate spread from accepted sample parameter values,
not from `MeasuredValue.confidence`. A transparent Tier-1 magnitude is:

```text
U_i = min(1, (q95_i - q05_i) / R_i)
```

where `q05_i` and `q95_i` are descriptive empirical quantiles of accepted
parameter samples and `R_i` is the declared evaluator range. A fixed parameter
has `U_i = 0`. If fewer than two valid samples exist, or parameter values are
missing, `U_i` is unavailable rather than zero. If `R_i` is zero, the parameter
is not eligible for this measure.

`U_i` is a normalized spread indicator. It is not a probability, confidence
level, posterior standard deviation, or claim that the declared range contains
the patient value. It also does not recover correlations that the current M5
request explicitly does not model.

## Uncertainty-impact heuristic boundary

For a metric target `m`, let `A_i,m` be the robust aggregate of finite local
responses across valid samples. The default aggregate is the median of
`abs(S_i,m)`; report the number of contributing samples and the interquartile
range alongside it. Define:

```text
uncertainty_impact_score_i,m = U_i * A_i,m
```

This is a **heuristic uncertainty-impact score**. It estimates which uncertain
input proxies have the greatest combination of current sampled spread and
local output responsiveness. It does not decompose output variance, establish
parameter identifiability, or prove that measuring the parameter will reduce
patient uncertainty.

For display, rank scores within the selected target and use `LOW`, `MODERATE`,
or `HIGH` only under a published configuration. Do not show percentages by
default. If a normalized bar is shown, label it `relative heuristic score`.
The value

```text
score_i,m / sum_j(score_j,m)
```

may be used as a display normalization only; it is **not** a variance share or
contribution percentage. A zero score can mean fixed input, low sampled spread,
low local response, unavailable perturbations, or an active clamp, so the UI
must retain the reason rather than claim “no effect.”

## Evidence priority boundary

An evidence-to-parameter map may use explicit constraint strengths:

| Strength | Tier-1 weight |
|---|---:|
| direct | `1.00` |
| strong | `0.75` |
| moderate | `0.50` |
| weak | `0.25` |
| no declared mapping | `0.00` |

For evidence type `e` and target metric `m`, the permissible Tier-1 ranking is:

```text
Evidence Priority Score(e,m)
  = sum over mapped parameters i
    uncertainty_impact_score_i,m * strength_weight(e,i)
```

This is a deterministic prioritization heuristic. It assumes the mapping and
weights are explicit, versioned, and reviewed. It must be labeled **Evidence
Priority Score** or **Estimated Uncertainty-Reduction Priority**, never
“expected information gain,” “information gain,” or “probability that a test
will help.” A recommendation can say which declared proxy the evidence is
intended to constrain; it cannot claim that the evidence will diagnose,
personalize, or improve care.

## What Tier 1 does not support

The following claims are outside this audit's mathematical boundary:

- global sensitivity or variance decomposition from local finite differences;
- Sobol indices, Morris measures, Shapley effects, or additive contribution
  percentages without their respective valid designs and estimators;
- parameter identifiability or proof that an input can be uniquely learned from
  the available outputs;
- posterior distributions, Bayesian updating, likelihoods, credible intervals,
  confidence intervals, or calibrated probabilities;
- expected information gain or entropy reduction, because no hypothetical
  observation model and posterior update are implemented;
- a medical measurement recommendation, diagnostic implication, treatment
  recommendation, or claim that a positive/negative simulated effect is good
  or harmful;
- a causal biological effect from a local model derivative;
- patient-specific uncertainty reduction from a population prior or synthetic
  replay;
- a correlation, covariance, or interaction effect that the M5 independent
  sampling contract does not represent;
- regional, electrical, PV-loop, or spatial sensitivity when the corresponding
  pointwise data is unavailable;
- uncertainty in a generated waveform or visualization inferred from scalar
  HR, RR, or cardiac metrics.

M6's safety disclaimer and hypothetical-simulation warnings remain mandatory
  on any API or UI surface that later exposes these scores.

## Tier-2 methods explicitly deferred

Sobol, Morris, Shapley, correlation-based global methods, and actual expected
information gain may be evaluated later, but only after defining the necessary
sampling design, joint parameter distribution, interaction treatment,
observation/noise model, posterior update, and validation tests. They must not
be represented by a Tier-1 score with a more prestigious name.

## Minimum reproducibility record

Any future implementation should persist:

```text
method = finite_difference
method_version
target_kind
metric_id and unit
parameter_id and unit
baseline sample ID and ensemble ID
baseline parameter value
projection-base identity or digest
lower/upper evaluator bounds
perturbation factor and effective step
difference scheme: central | forward | backward
baseline, perturbed, and raw response values
parameter/output scaling policy
uncertainty spread definition and quantiles
constraint-map version, if evidence ranking is shown
valid/unavailable counts and boundary flags
seed, origin snapshot, physiology/distribution/prior versions
```

The record must be deterministic for the same persisted ensemble, scenario,
configuration, and model versions. No LLM output may select a perturbation,
compute a derivative, assign a constraint strength, or override an unavailable
result.

## Audit conclusion

M8 can begin with a mathematically honest Tier-1 engine over the existing
five-dimensional bounded proxy space. The correct first product is a
target-specific, unit-aware, lineage-preserving local response analysis plus a
clearly labeled uncertainty-impact and evidence-priority heuristic. Anything
that claims more than local deterministic responsiveness and sampled spread
requires a new statistical contract and must not be inferred from the current
M5.5/M6 data.
