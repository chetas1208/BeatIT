# M6 Decisions

- M5.5 Python projection remains the sole numerical evaluator for M6.
- Scenario values are bounded before execution and applied to each existing
  baseline sample; M6 performs no latent-parameter resampling.
- Pair IDs retain the original baseline sample ID and use a trial-namespaced
  scenario identity.
- Persisted pair IDs are trial-namespaced as
  `<trial_id>-scenario-<baseline_sample_id>`; the compact helper form remains
  available only for standalone identity tests.
- Scenario parameter declaration order is canonicalized by parameter ID. The
  `value` field is an absolute bounded target; optional `baseline` and `delta`
  fields are descriptive origin metadata and are not interpreted as a
  per-sample additive operation.
- Effect distributions use explicit units and metric-specific neutral
  tolerances. Direction is descriptive, never a clinical value judgment.
- Shadow Trial results are persisted in the existing file-backed SQLite path.
  Records are immutable and same-input replays are idempotent.
- M6 uses synchronous thread-offloaded execution for the current 50–1000 pair
  envelope; no fake progress stream is added.
- PV comparison remains scalar/unavailable until canonical pointwise PV data
  exists. No M7 split-heart rendering is included.
- M6 demo fixtures are synthetic and visibly labeled; they are not patient
  evidence.
