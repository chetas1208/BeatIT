# M7 Preflight — M6 Shadow Trial Boundary

Status: **CONDITIONAL PASS — M7 may proceed on the paired-result contract.**

## Evidence

- Focused M6 suite: `40 passed, 8 warnings` using
  `PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev pytest -q python/hearttwin/tests/test_shadow_trial_*.py`.
- M6 uses one persisted M5.5 ensemble and applies each scenario to the same
  sample's stored parameter vector. The engine does not resample a scenario
  ensemble.
- Pair contracts preserve `sample_id`, `baseline_twin_id`,
  trial-namespaced `scenario_twin_id`, baseline/scenario parameters, typed
  deltas, validity, and rejection reasons.
- SQLite storage round-trips complete trial results and rejects conflicting
  immutable writes; identical deterministic replay is idempotent.
- Scenario declaration order is canonicalized before trial identity and
  provenance are computed.

## Boundaries carried into M7

- M7 consumes persisted pair DTOs and existing visual projection helpers. It
  must not recompute cardiac physiology in TypeScript or pair unrelated
  samples.
- Existing conditional M6 findings remain active: browser/accessibility
  validation is unavailable in this environment, security is demo-only, and
  the scalar PV boundary does not provide pointwise uncertainty envelopes.
- The typed scenario BP fields remain a documented projection caveat; canonical
  MAP remains the numerical authority.
- A pair with `valid: false` is not eligible for the split-heart view.

## M7 integration rule

The split view receives one valid `ShadowTrialPair` and an existing baseline
visualization template. The baseline and counterfactual state objects are
passed explicitly to two independent renderers. Any deformation, flow,
electrical, or PV display is a downstream educational projection and must keep
its source/limitation labels.
