# M6 Statistical Integrity Review

Date: 2026-09-26  
Scope: read-only audit of paired Shadow Trial deltas, raw metric values,
category tolerances, percentile summaries, invalid-pair handling, and
zero-valid-pair behavior. No implementation files were changed. M7 Split Heart
and M8 Missing Piece are out of scope.

## Verdict

**Calculation mechanics: PASS. Reproducibility contract: CONDITIONAL.**

The current engine calculates descriptive effects from identity-preserving
pairs and does not resample a scenario population. Raw finite deltas, explicit
units, metric-specific neutral tolerances, category counts, and quantiles are
implemented consistently. Invalid pairs are retained for auditability and are
excluded from effect distributions; a run with no valid pairs produces empty
summaries rather than fabricated zero effects.

The remaining statistical-integrity blocker is identity metadata: a caller can
override `neutral_tolerance`, changing positive/near-zero/negative counts,
without changing the trial fingerprint or persisted provenance. The same
trial ID can therefore describe different categorical summaries. This must be
closed before claiming replay-complete statistical reproducibility.

## Evidence executed

Focused M6 suite:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_shadow_trial_contracts.py \
  python/hearttwin/tests/test_shadow_trial_golden.py \
  python/hearttwin/tests/test_shadow_trial_identity.py \
  python/hearttwin/tests/test_shadow_trial_store.py

27 passed, 8 warnings in 0.34s
```

A direct metrics probe confirmed empty-distribution semantics and the inclusive
tolerance boundary. A separate probe produced:

```text
same_fingerprint True
categories_low [0, 0, 3]
categories_high [0, 3, 0]
```

The two runs used the same ensemble, scenario, and metric but different neutral
tolerances (`0.0` and `100.0`). Category counts changed while the fingerprint
remained equal.

## 1. Paired delta integrity

The pairing path in `python/hearttwin/shadow_trial_engine.py` has the required
same-twin shape:

1. Ensemble samples are sorted by `(sample.id, sample.index)`, so input list
   order does not affect output order.
2. Each scenario parameter map starts as a copy of that sample's persisted
   parameters; only declared scenario parameters are replaced.
3. Scenario evaluation uses the sample's persisted `projection_base`, not a
   newly sampled population and not a baseline reconstructed from an already
   projected scenario state.
4. Persisted sample outputs remain the baseline authority.
5. Each delta is calculated as `scenario value - baseline value`.

`test_mixed_sample_scenario_uses_persisted_projection_base_once` covers a mixed
sample distribution and compares the result with the canonical evaluator.
`test_noop_scenario_has_exact_zero_deltas_and_does_not_mutate_ensemble` covers
the identity case: a no-op produces exact zero deltas and leaves the input
ensemble unchanged. `test_pairing_is_order_independent_and_reproducible`
covers order-independent replay.

The engine preserves raw floating-point deltas. It does not round values before
calculating means, quantiles, or category counts. This is appropriate for the
deterministic educational simulation, provided consumers treat serialized
floating-point values as replay values within the documented tolerance policy,
not as measured clinical precision.

### Pair-level contract gap

`PairedTwinResult` validates finite deltas and the valid/invalid reason rule,
but it does not enforce all statistical fields that the engine currently
produces:

- `delta_units` is not required to be complete or match the canonical unit
  for every delta.
- `baseline_parameters`, `scenario_parameters`, and the legacy
  `parameters` map are not cross-validated for same-sample identity.
- The pair contract has no parameter digest or sample-index field.
- A valid pair can be constructed with a partial metric set; the selected
  metric set lives outside the pair model.

The engine path currently emits the expected complete values, but direct
deserialization or future producers could create a result whose summary is not
fully traceable to its pair payload. These are contract-hardening items, not
evidence that the current happy path resamples.

## 2. Raw values, units, and summaries

`EffectDistribution` stores the complete valid-pair delta list in `deltas`
and also stores `mean_delta`, `median_delta`, fixed quantile keys, category
counts, and `neutral_tolerance`. The contract rejects non-finite deltas and
requires category counts to sum to the number of stored deltas.

Units come from the backend-owned `METRIC_UNITS` map and are checked again by
the Pydantic model:

| Metric | Unit |
| --- | --- |
| `ejection_fraction_pct` | `percentage_points` |
| `stroke_volume_ml` | `mL` |
| `cardiac_output_l_min` | `L/min` |
| `heart_rate_bpm` | `bpm` |
| `map_mmhg` | `mmHg` |
| `edv_ml`, `esv_ml` | `mL` |
| `pv_loop_area_index` | `index` |

The percentage change is intentionally represented as percentage points, not a
relative percentage. Category names are descriptive simulation directions; they
do not encode clinical benefit or harm.

One presentation boundary remains important: `pv_loop_area_index` is a
declared metric, but the canonical M5.5 evaluator does not calculate a new PV
loop value. The current missing-PV test correctly makes pairs invalid when the
field is unavailable. The metric must remain unavailable/invalid rather than
being interpreted as a computed unchanged value if a copied state field is
present in a future path.

## 3. Category tolerance policy

The implementation uses metric-specific defaults from
`NEAR_ZERO_TOLERANCES`:

| Metric family | Tolerance |
| --- | ---: |
| EF, SV, HR, MAP, EDV, ESV | `0.01` in the metric's unit |
| Cardiac output | `0.001 L/min` |
| PV loop area index | `0.001 index` |

Classification is inclusive at the neutral boundary:

```text
positive:  delta > tolerance
near-zero: abs(delta) <= tolerance
negative:  delta < -tolerance
```

This partitions every finite delta exactly once. The contract recomputes the
three counts from stored raw values and rejects mismatches. A custom finite,
non-negative `neutral_tolerance` is accepted by the engine, which is useful
for explicit exploratory analysis but makes the identity gap above material.

Required closure:

- Include the effective tolerance policy, including per-metric overrides, in
  the trial definition, provenance, and trial fingerprint.
- Add a replay test asserting that changing tolerance changes identity and
  persisted categorical output, while semantically identical canonical input
  order remains identity-stable.

## 4. Percentile interpolation and interpretation

`quantile()` sorts a copy of the input and uses the linear interpolation
position `(n - 1) * p`. For non-integral positions it interpolates between
adjacent order statistics. The engine and contract use the same convention for
q05, q25, median/q50, q75, and q95, with finite-value validation and a
`1e-12` relative/absolute consistency check in the contract.

This is a deterministic descriptive percentile convention. The q05–q95 span is
not a confidence interval, credible interval, probability, efficacy estimate,
or patient-specific likelihood. The implementation does not perform bootstrap
resampling or inferential testing, which is correct for the current bounded
simulation contract.

Focused contract tests verify mean, median, quantile, count, and unit
consistency on stored distributions. A stronger regression fixture should add
an asymmetric multi-point vector with hand-computed q05/q25/q75/q95 values so
the interpolation convention remains visible independently of the engine.

## 5. Invalid-pair exclusion

The engine attempts one pair for every baseline sample, including samples that
were already rejected by M5.5. An invalid pair remains in `paired_results` with
`valid=false` and explicit `rejection_reasons`; it contributes neither raw
deltas nor effect-distribution values. The result separately reports
`requested_pairs`, `valid_pairs`, and `invalid_pairs`, and emits a warning
when invalid pairs exist.

`test_invalid_pair_is_retained_and_excluded_from_effects` verifies that a
missing baseline state metric is retained as one invalid pair while every
distribution contains only valid-pair values. Distribution validation then
checks that its raw delta list is exactly the valid-pair subset for that metric.

The engine's normal path clears `deltas` for a pair that accumulates a
rejection reason. The Pydantic contract does not explicitly forbid a hand-built
invalid pair from containing partial deltas, nor does it encode the selected
metric set at the pair level. Add a contract test or validator so invalid pairs
cannot be mistaken for partially observed valid effects in pair inspection.

## 6. Zero-valid-pair behavior

When no pair is valid, the engine returns:

- `status="failed"`;
- `valid_pairs=0` and `invalid_pairs=requested_pairs`;
- one retained invalid pair per requested baseline sample;
- one effect distribution per selected metric with an empty `deltas` list,
  zero category counts, and null mean/median/quantiles;
- an explicit warning that no valid paired outcomes are available.

The missing-PV test exercises this path and confirms that the engine does not
fabricate a zero delta. `EffectDistribution` independently rejects non-empty
summaries for an empty distribution.

The result validator checks count reconciliation and distribution contents but
does not fully couple `status` to `valid_pairs`: a manually constructed
result could potentially claim `complete` with zero valid pairs or `failed`
with valid pairs. It also does not require the definition's metric set to equal
the distribution metric set in every zero/non-zero case. The engine's emitted
result is consistent; the wire contract should enforce the same invariant.

## 7. Findings and closure gates

| Priority | Finding | Current evidence | Closure gate |
| --- | --- | --- | --- |
| P0 | Tolerance overrides change categories without changing trial identity | Direct probe: same fingerprint, different counts | Hash and persist effective tolerance policy; replay test |
| P1 | Pair contract does not require complete units/metric coverage or parameter identity | Validators cover finiteness but not cross-field completeness | Add validators and tamper tests |
| P1 | Result status and selected metric set are not fully coupled to distributions | Engine is correct; model permits weaker hand-built payloads | Add result-level invariants and zero-valid tests |
| P1 | PV metric has no canonical counterfactual evaluator | Missing-PV path is correctly invalid | Keep excluded until a canonical output exists |
| P2 | Interpolation convention lacks an explicit asymmetric hand-vector fixture | Current focused tests pass | Add a golden quantile vector |

These findings do not justify changing deterministic cardiac formulas. The
appropriate repair boundary is the M6 contract, identity, and statistics layer.

## Scope boundary

This review covers paired statistical summaries only. It does not introduce a
second heart, split viewport, treatment ranking, missing-piece inference,
clinical recommendation, or any M7/M8 behavior.
