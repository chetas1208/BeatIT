# M8 Mathematical Review

Status: **INITIAL FAIL FINDINGS CLOSED — Tier-1 release re-review passed**  
Date: 2026-09-26  
Scope: current M8 contracts, perturbation policy, local sensitivity, uncertainty
spread, impact ranking, evidence ranking, and `run_missing_piece` orchestration.

This is a read-only adversarial review. No code was changed.

## Executive result

The initial adversarial pass below intentionally recorded release blockers.
Those findings were subsequently closed by the lead integration pass and are
retained as an audit trail. The current contract boundary rejects unsupported
global-method labels, unavailable sensitivities carry no numeric response,
invalid samples retain reasons, normalized magnitudes are aggregated before
ranking, and the M6 paired-effect orchestration path is implemented.

The primary baseline-output finite-difference path is defensible: it uses the
persisted projection base, bounded native-unit perturbations, one-sided behavior
at domain edges, and an explicit dimensionless response scale. The evidence
ranking is also correctly described as an Evidence Priority Score rather than
information gain.

The M8 math/contracts gate nevertheless fails. The current surface can silently
omit invalid samples, can represent unavailable sensitivity with numeric values,
can fall back to mixed-unit raw derivatives, and does not implement sensitivity
of an M6 Shadow Trial effect. The public contracts also accept unsupported
Sobol/Shapley labels even though no such computation exists.

## Findings

| ID | Area | Result | Finding and evidence |
|---|---|---|---|
| P1 | Raw derivative units | **PASS, with auditability gap** | `engine.py:92-115` evaluates the canonical output and divides the output delta by the native parameter step. This yields units such as `mL/index`, `L/min/bpm`, `percentage-points/index`, or `bpm/bpm`. The calculation is correct for the supported evaluator. `ParameterSensitivity` does not carry explicit parameter/output unit fields, so consumers cannot verify those units from the contract alone. |
| P2 | Bounds and one-sided differences | **PASS** | `PerturbationPolicy` validates against `PARAMETER_BOUNDS`, caps the step at five percent of the declared range, and selects central/forward/backward differences at the boundary. `engine.py:94-113` uses that policy and never intentionally evaluates outside the domain. |
| P3 | Normalized scaling | **PASS in engine** | `engine.py:114-115` implements `D * max(abs(theta), 0.5*range) / max(abs(Y), floor)`, matching the reviewed Tier-1 formula. The metric floors are explicit in `engine.py:32-40`. |
| P4 | Empirical uncertainty magnitude | **PASS** | `uncertainty.py:38-70` uses accepted finite sample parameters and `q05/q95` divided by the declared parameter range. Fewer than two usable values are marked unavailable rather than zero. It does not interpret confidence metadata as probability. |
| P5 | Heuristic terminology in the normal path | **PASS** | `impact.py:11,29-33`, `evidence_value.py:24-29`, engine limitations, and `M8_INFORMATION_GAIN_BOUNDARY.md` consistently identify the product as an uncertainty-impact heuristic or Evidence Priority Score and explicitly reject information-gain claims. |
| P6 | Unsupported global calculation in the aggregator | **PASS locally** | `global_sensitivity.py:60-72` rejects records labeled `sobol`, `morris`, or `shapley` instead of reinterpreting them. Its output is explicitly a local-response aggregate. |
| P7 | Numerical authority and determinism | **PASS for valid samples** | `engine.py:87-105` re-evaluates the persisted `projection_base` and parameters, rather than trusting stored output fields. The focused review test confirms tampering with stored outputs does not change the result. Sorting by sample ID/index and deterministic medians are reproducible. |
| F1 | Shadow Trial effect drivers | **FAIL — release blocker** | The reviewed math requires a target kind for either a baseline output or an M6 paired effect. `run_missing_piece` accepts only an ensemble and `target_metric` (`engine.py:156-161`); it never accepts a Shadow Trial/scenario or computes `Y_scenario - Y_baseline`. `ParameterSensitivity` has no target-kind/effect contract. The `shadow_trial_id` fields are lineage-only and do not make effect sensitivity exist. M8 therefore cannot answer uncertainty drivers for the M6 effect it claims to support. |
| F2 | Unsupported global-method claims at the contract boundary | **FAIL** | `SensitivityMethod` explicitly permits `sobol` and `shapley` (`contracts.py:18`), and a direct probe successfully constructed both labels without any global calculation. `ParameterUncertaintyImpact.method` and `EvidenceValueEstimate.method` are unrestricted strings, so a caller can also label a heuristic as expected information gain. Rejecting labels in one aggregator is insufficient; the public DTO boundary must not accept unsupported claims. |
| F3 | Unavailable sensitivity representation | **FAIL** | `ParameterSensitivity` requires numeric `sensitivity` and `baseline_value` even when `available=False` (`contracts.py:80-119`). It accepts an unavailable record containing a numeric derivative and perturbation. That permits downstream code to treat unavailable data as usable. The contract should make unavailable records structurally non-numeric or require a reason and prevent impact participation. |
| F4 | Invalid-sample handling | **FAIL** | `_sample_sensitivity` returns `([], None)` for every invalid sample (`engine.py:83-86`). Those samples are silently omitted, while `sensitivity_availability.unavailable_sample_count` counts only explicit reasons (`engine.py:207-214`). If all samples are invalid, the result reports no unavailable reasons. This violates the required explicit unavailable accounting and makes “available” dependent on silent filtering. |
| F5 | Aggregate magnitude is mathematically wrong for the stated method | **FAIL** | The stated method is median absolute local response, but `engine.py:189-194` takes a median of signed `sensitivity` and signed `normalized_sensitivity`, then `impact.py:47-54` applies `abs` only after aggregation. Opposing sample responses can cancel before magnitude is computed. The engine also does not expose the q25/q75/IQR from `global_sensitivity.py`; the robust spread promised by the math audit is therefore absent from the public result. |
| F6 | Mixed-unit fallback in impact ranking | **FAIL** | `impact.py:47-52` uses `normalized_sensitivity` when present but falls back to raw `item.sensitivity` when it is absent. Raw derivatives across parameters are not comparable when parameter/output units differ. The engine currently supplies normalized values, but the public helper and contract allow an unsafe path. Missing normalization must be unavailable/rejected, not silently ranked. |
| F7 | Scaling provenance is incomplete | **FAIL** | The engine records the resulting step and a prose assumption (`engine.py:128-139`), but not the perturbation mode, the five-percent cap/configuration, the actual parameter scale, the numeric metric floor, or explicit units. The standalone `run_local_sensitivity` path does not populate `normalized_sensitivity` at all (`sensitivity.py:179-196`). Two mathematically different configurations can therefore produce records that look equivalent to consumers. |
| F8 | Claim boundary is documented but not enforced | **FAIL, containment gap** | The documentation boundary is strong, but contracts use free-form method strings and `estimated_reduction` is a generic `[0,1]` field (`contracts.py:203-241`). There is no schema-level invariant preventing an API caller from presenting that field or method as a probability, expected reduction, or information gain. Safety depends on caller discipline rather than the DTO. |

## Required disposition

The following are required before declaring the M8 math/contracts gate passed:

1. Add an explicit baseline-output versus Shadow-Trial-effect target contract and
   implement paired, same-sample effect perturbations with the M6 scenario held
   fixed according to the reviewed rules.
2. Make unsupported global methods impossible at the public contract boundary;
   retain explicit rejection tests for Sobol, Morris, and Shapley claims.
3. Represent unavailable sensitivity as unavailable with a reason and no usable
   numeric derivative; count invalid samples and preserve their reasons.
4. Aggregate `abs(normalized_sensitivity)` per sample before taking the median,
   and expose contributing count plus q25/q75 or an equivalent explicit spread.
5. Remove the raw-derivative fallback from uncertainty-impact ranking. Require a
   versioned normalized response for cross-parameter ranking.
6. Persist the complete sensitivity configuration and unit metadata, including
   perturbation mode/factor, cap, parameter scale, output floor, and target kind.

## Closure verification

- `python/hearttwin/tests/test_missing_piece_*.py`: **64 passed**.
- `ruff check python/hearttwin/missing_piece python/hearttwin/storage/missing_piece_store.py python/hearttwin/tests/test_missing_piece_*.py`: **All checks passed**.
- `run_missing_piece_shadow_effect(...)` smoke test produced explicit
  `target_kind="shadow_effect"` records over the persisted M5.5 projection
  base and fixed absolute scenario target.
- Contract tests now reject `sobol`/`shapley` labels and numeric unavailable
  records; impact ranking rejects missing normalized responses.

The historical findings below remain useful regression requirements; their
original FAIL labels describe the pre-closure state, not the current state.

## Verification evidence

The focused M8 test suite passed:

```text
python -m pytest -q python/hearttwin/tests/test_missing_piece_*.py
60 passed in 0.39s
```

That suite verifies the intended happy paths and several boundary cases, but it
does not cover the release-blocking failures above. A direct contract probe also
confirmed that `sobol` and `shapley` records, numeric unavailable records, and an
arbitrary `expected-information-gain-v1` impact method are currently accepted.
