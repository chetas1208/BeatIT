# M6 Effect Statistics and Invalid-Pair Review

Date: 2026-09-26  
Scope: read-only review of `shadow_trial_contracts.py`, `shadow_trial_metrics.py`,
`shadow_trial_engine.py`, and every `test_shadow_trial*.py` test. Covered:
metric units, neutral thresholds, empty distributions, rejection retention, and
count reconciliation. No implementation files were changed. M7 Split Heart and
M8 Missing Piece are out of scope.

## Verdict

**Conditional pass.** The active engine produces finite paired deltas with
explicit units, metric-specific inclusive neutral thresholds, empty summaries
for zero valid pairs, and reconciled pair counts. All focused shadow-trial tests
pass.

Bounded findings remain:

1. A pair that becomes invalid after an earlier metric succeeds can retain a
   partial `deltas` map. The values are excluded from distributions but make
   the invalid payload look partially valid.
2. The Pydantic envelope does not fully enforce pair units, empty quantiles, or
   the relationship between result `status` and `valid_pairs`.

No arithmetic error, cross-sample resampling, or valid-distribution
contamination was detected on the current engine path.

## Verification

Command:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q python/hearttwin/tests/test_shadow_trial*.py
```

Result:

```text
40 passed, 8 warnings in 1.46s
```

The warnings are the existing Pydantic deprecation warning for
`datetime.utcnow()` in contract-test fixture construction. The glob covered
engine, contract, API, golden-fixture, identity, reproducibility, and SQLite
persistence tests.

## 1. Metric units

The contract defines eight metrics and units in
`METRIC_UNITS` (`shadow_trial_contracts.py:22-44`):

| Metric | Unit |
| --- | --- |
| `ejection_fraction_pct` | `percentage_points` |
| `stroke_volume_ml` | `mL` |
| `cardiac_output_l_min` | `L/min` |
| `heart_rate_bpm` | `bpm` |
| `map_mmhg` | `mmHg` |
| `edv_ml`, `esv_ml` | `mL` |
| `pv_loop_area_index` | `index` |

`effect_distribution()` derives units from that map
(`shadow_trial_metrics.py:30-68`), and `EffectDistribution` validates them
against the same map (`shadow_trial_contracts.py:259-263`). The engine emits
pair units from the map (`shadow_trial_engine.py:226-237`). Tests assert
percentage points for EF, mL for SV, L/min for CO, bpm for HR, and reject `%`
for EF (`test_shadow_trial_engine.py:53-58`,
`test_shadow_trial_contracts.py:105-124`).

PV is not fabricated: requesting it produces invalid pairs and an empty
distribution (`test_shadow_trial_engine.py:140-152`).

### Finding U1 — pair-level units are not contract-validated (P1)

`PairedTwinResult` checks finite delta values but does not require
`delta_units` to contain exactly the delta keys or match `METRIC_UNITS`
(`shadow_trial_contracts.py:192-222`). The contract test helper constructs a
valid EF pair with no `delta_units` (`test_shadow_trial_contracts.py:64-74`).
The engine-generated map is correct; a hand-built or tampered pair can still
omit or mislabel a unit. This is a traceability gap, not an observed engine
unit error.

## 2. Neutral thresholds

Defaults in `NEAR_ZERO_TOLERANCES` are
(`shadow_trial_contracts.py:46-54`):

- EF, SV, HR, MAP, EDV, ESV: `0.01` in the metric unit;
- CO: `0.001 L/min`;
- PV-loop area index: `0.001 index`.

The classifier validates finite non-negative tolerances and uses
(`shadow_trial_metrics.py:36-44`):

```text
positive:  delta > tolerance
neutral:   abs(delta) <= tolerance
negative:  delta < -tolerance
```

A direct boundary probe gave:

```text
ejection_fraction_pct: tolerance=0.01, values=[0.01, -0.01, 0.011, -0.011, 0.0], counts=[1, 3, 1]
cardiac_output_l_min: tolerance=0.001, values=[0.001, -0.001, 0.0011, -0.0011, 0.0], counts=[1, 3, 1]
```

Signed boundary values are neutral and every finite value is classified once.
The contract recomputes category counts and rejects tampered counts
(`shadow_trial_contracts.py:274-284`).

Custom tolerance values are included in the trial identity
(`shadow_trial_engine.py:150-162`). Direct afterload probes showed different
fingerprints and categories for tolerance `0.0` versus `100.0`:

```text
tolerance=0.0   categories=[0, 0, 3]  fingerprint=d0d13dd02ad68821761e224f4409fcf6711148950b6ff374245e78e9e0ffdb80
tolerance=100.0 categories=[0, 3, 0]  fingerprint=95bca5bdfea7973fe8ee37016d871349b8f9690b3b59aa478ee6fa0cce17982d
```

The older suspected tolerance/fingerprint ambiguity is not present in this
revision.

## 3. Empty distributions

For empty input, `effect_distribution()` returns no deltas, null mean/median,
null q05/q25/q75/q95, and zero category counts
(`shadow_trial_metrics.py:45-67`). The missing-PV path retains every invalid
pair, reports `valid_pairs=0` and `invalid_pairs=requested_pairs`, and emits
an empty distribution rather than a fabricated zero
(`test_shadow_trial_engine.py:140-152`).

### Finding E1 — empty quantiles are under-constrained (P2)

The empty contract branch rejects nonzero category counts and non-null mean or
median, but does not require all quantiles to be null
(`shadow_trial_contracts.py:266-271`). A direct probe was accepted:

```text
empty_quantiles_contract accepted {'q05': 0.0, 'q25': None, 'q75': None, 'q95': None}
```

The engine output is correct; the wire contract permits a misleading
hand-built empty summary. Require all empty quantiles to be null.

## 4. Rejection retention and invalid-pair exclusion

The missing-baseline test removes EDV/ESV from one sample. It verifies one
retained invalid pair with reasons and no deltas, `invalid_pairs=1`,
`valid_pairs=2`, and distributions containing only two values
(`test_shadow_trial_engine.py:93-121`). This is the desired audit shape.

### Finding R1 — partial deltas survive invalidation (P1)

When a later requested metric is unavailable, the engine appends a rejection
reason but does not clear deltas already collected
(`shadow_trial_engine.py:212-239`). A direct three-sample probe requesting
EF plus unavailable PV produced:

```text
requested=3 valid=0 invalid=3
distribution_lengths=[0, 0]
pair_deltas=[{'ejection_fraction_pct': 0.0}, {'ejection_fraction_pct': 0.0}, {'ejection_fraction_pct': 0.0}]
pair_reasons=[['pv_loop_area_index: metric is unavailable in baseline or scenario state'], ...]
```

The partial EF values do not enter distributions because only valid pairs are
passed to `effect_distribution()` (`shadow_trial_engine.py:240-245`), so
current statistics are not contaminated. However, an invalid pair should carry
states and rejection reasons, not partial effect data that a consumer could
mistake for a valid observation.

Bounded repair: calculate deltas in temporary storage and publish them only
after all selected metrics succeed, or clear both `deltas` and
`delta_units` whenever a rejection is recorded. Add an EF-plus-unavailable-PV
regression test.

## 5. Count reconciliation

`ShadowTrialResult` enforces
`valid_pairs + invalid_pairs == requested_pairs`, retained-pair length,
valid-flag count, unique sample IDs, and valid-pair distribution coverage
(`shadow_trial_contracts.py:362-388`). It also checks that each distribution's
raw values match valid pairs and that category counts match raw delta count and
sign classification. The engine populates the fields from the retained pairs
(`shadow_trial_engine.py:240-307`). The API effects projection separately
checks pair-count reconciliation.

### Finding C1 — result status is not coupled to valid count (P2)

The engine emits `complete` when at least one pair is valid and `failed`
when none are valid (`shadow_trial_engine.py:295-309`), but the result
validator does not enforce that relationship. Direct validation accepted both:

```text
valid result with status='failed'       -> accepted
zero-valid result with status='complete' -> accepted
```

This does not affect engine-generated results, but weakens persisted-payload
integrity. Require `complete` with `valid_pairs > 0` and `failed` with
`valid_pairs == 0`, or document a third status.

The zero-valid branch also skips distribution-metric equality because it is
conditional on `valid_pairs > 0`; clearing invalid partial deltas closes the
resulting ambiguity.

## Findings summary

| Priority | Finding | Evidence | Bounded closure |
| --- | --- | --- | --- |
| P1 | Pair `delta_units` is not checked against delta keys | Valid test helper pair omits units | Require exact valid-pair key/unit correspondence |
| P1 | Invalid pairs can retain partial deltas | EF plus unavailable-PV probe retained EF deltas | Publish effects only after all selected metrics succeed |
| P2 | Empty distributions accept non-null quantiles | Direct `q05=0.0` probe accepted | Require all empty quantiles to be null |
| P2 | Result status is not coupled to valid count | Both status/count tamper probes accepted | Validate status against `valid_pairs` |

## Scope boundary

No implementation files were changed. This review does not assess clinical
validity, treatment efficacy, M7/M8 behavior, frontend rendering, or browser
accessibility. Findings are limited to the backend M6 effect-statistics and
invalid-pair contracts.

## Post-review resolution

The lead tightened the three contract gaps: pair `delta_units` must exactly
cover returned deltas with canonical units, empty distributions require null
summary/quantile values, and result status is coupled to the valid-pair count.
Invalid pairs are now atomic for effect reporting: partial deltas are cleared
while states and rejection reasons remain available. The focused M6 suite
passes 40 tests; the remaining limitation is diagnostic-only retained invalid
state, not a published effect.
