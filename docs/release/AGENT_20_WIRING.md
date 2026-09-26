# M10.5 Agent 20 — Numerical and Provenance Wiring Audit

**Date:** 2026-09-26  
**Scope:** representative EF, stroke volume, cardiac output, provenance, scenario deltas, report values, and persistence across domain, API, and UI boundaries.  
**Disposition:** **PASS for the exercised local synthetic ensemble/Shadow Trial path; OPEN for the unified report surface and browser-visible E2E verification.**

This is a wiring audit, not a validation of the physiological model or a clinical claim. Values below are synthetic fixture outputs.

## Representative end-to-end trace

The read-only probe used `fixtures/golden/probabilistic/synthetic-replay.json`, temporary SQLite databases, the real FastAPI routes, and one valid persisted sample. It created an ensemble, reloaded it, created an afterload scenario (`1.0 → 1.2`), and reloaded the Shadow Trial.

| Metric | Ensemble sample state | Ensemble `outputs` | Baseline pair state | Counterfactual state | Persisted delta | Delta check |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| EF (%) | 54.473684210526315 | 54.473684210526315 | 54.473684210526315 | 50.526315789473685 | -3.94736842105263 percentage points | PASS |
| Stroke volume (mL) | 67.275 | 67.275 | 67.275 | 62.4 | -4.875000000000007 mL | PASS |
| Cardiac output (L/min) | 4.574700000000001 | 4.574700000000001 | 4.574700000000001 | 4.2432 | -0.331500000000001 L/min | PASS |

For all three metrics, the state value equaled the canonical sample output. For the pair, each persisted delta equaled `counterfactual - baseline` within `1e-12`. Ensemble and Shadow Trial GET responses were exactly equal as decoded JSON objects to their POST responses in the probe.

## Boundary trace

### Domain and API

1. `python/hearttwin/ensemble.py:_evaluate` computes the canonical scalar outputs. The order is explicit: EDV/ESV, then `SV = EDV - ESV`, `CO = HR × SV / 1000`, and `EF = SV / EDV × 100` (`ensemble.py:365-375`).
2. `_derived_state` copies those outputs into typed `MeasuredValue` fields for `ejection_fraction_pct`, `stroke_volume_ml`, and `cardiac_output_l_min`, with units, `ValueSource.DERIVED`, confidence `1.0`, and a method string (`ensemble.py:378-396`).
3. The ensemble route validates the canonical `EnsembleResponse` and persists the complete payload before returning it (`api.py:229-252`). The distributions route exposes distributions plus ensemble provenance (`api.py:255-268`).
4. `run_shadow_trial` reuses each persisted sample's `projection_base`, applies only the declared scenario target, preserves persisted baseline outputs as the baseline authority, reads baseline/scenario metric values, and stores raw deltas (`shadow_trial_engine.py:114-144`, `:197-243`). This avoids sampling a second population or applying sampled parameters twice.
5. The Shadow Trial route persists the validated payload and all read routes revalidate it before exposure (`api.py:347-425`).

### Persistence

- `SQLiteEnsembleStore` serializes the complete response JSON and opens a connection per operation, supporting cross-process/restart reads (`storage/ensemble_store.py:52-117`).
- `SQLiteShadowTrialStore` uses canonical sorted JSON, create-once semantics, and rejects a conflicting rewrite of an existing trial ID (`storage/shadow_trial_store.py:51-116`).
- The probe confirmed exact ensemble and Shadow Trial readback using temporary stores. This does not certify PostgreSQL, Valkey/Redis, backup/restore, or deployed restart behavior.

### Frontend API/domain adapter

- `web/lib/api.ts` sends the ensemble and Shadow Trial requests to the matching `/api/v1` routes and returns typed JSON without recalculating values.
- `web/lib/twin/ensemble/adapter.ts:5-64` maps backend metric IDs, units, samples, summary statistics, representative IDs, and provenance versions into the frontend domain. It intentionally does not retain backend `outputs` or `projection_base`; the mapped sample `state.measurements` is the frontend scalar source.
- The frontend `CardiacTwinState` and `MeasuredValue` shapes mirror the Python fields and preserve `value`, `unit`, `source`, `confidence`, method, and evidence metadata (`web/types/heart.ts`).

### UI destinations

| Surface | Value source | Wiring result |
| --- | --- | --- |
| Plausible Twins | `ensemble.distributions` for medians/quantiles; representative `sample.state.measurements.ejection_fraction_pct` for EF labels | PASS; no frontend physiology recomputation (`PlausibleTwinsPanel.tsx:20-26`, `:90-108`). |
| Copilot operate card | `visualization.summary` first, then `state.measurements` as fallback | PASS for the operate response shape; values are read defensively (`CopilotDock.tsx:69-102`). |
| Split Heart / comparison | `pair.baseline_state`, `pair.scenario_state`, and persisted `pair.deltas` | PASS; `buildMetricDelta` treats the DTO delta as authoritative and only reads side values from state (`differences.ts:39-50`). |
| Paired visualization | State metrics copied into visualization summaries and cardiac-cycle fields; PV loop shape held from the reference visualization | PASS as a scalar projection, not a new physiological computation (`comparison/projection.ts:15-49`). |
| M4 Scenario Inspector | `ScenarioResult.componentDeltas` and `ScenarioResult.provenance` | PASS in the typed local scenario path; the table renders baseline, scenario, delta, unit, and detailed provenance (`ScenarioInspector.tsx:64-124`). |
| Unified REPORT mode | Boolean readiness flags, section summaries, and a short list of IDs | **OPEN gap:** `ReportSurface` does not receive or render EF, SV, CO, scenario deltas, or detailed provenance. It is a session completeness/status report, not a numerical report (`ReportSurface.tsx:20-60`, `reportContracts.ts:21-58`). |

## Provenance continuity

The exercised ensemble carried:

- `origin_snapshot_id`: `golden-synthetic-replay`
- `origin_quality`: `synthetic`
- origin source: `synthetic_replay`
- evidence IDs: `golden-probabilistic-fixture`, `golden-synthetic-replay`
- seed: `404`
- physiology version: `m5.5-ensemble-projection-v1`
- distribution version: `m5.5-backend-ensemble-v1`
- prior version: `m5-priors-v1`

The Shadow Trial retained the origin, ensemble, scenario-definition hash, scenario parameter changes, seed, engine/version metadata, evidence IDs, and pairing assumptions. The frontend ensemble adapter preserves these fields in its domain provenance object. The comparison provenance projection also validates origin/definition/ensemble identity and preserves pair identity and rejection lineage.

One presentation limitation remains: the unified REPORT surface reduces provenance to `[snapshot ID, ensemble ID, pair ID]`. Detailed source, method, confidence, evidence, and version fields remain available in the ensemble/comparison/scenario-specific surfaces but are not rendered in the unified report.

## Checks run

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev pytest -q \
  python/hearttwin/tests/test_ensemble_api.py \
  python/hearttwin/tests/test_shadow_trial_api.py \
  python/hearttwin/tests/test_shadow_trial_reproducibility.py \
  python/hearttwin/tests/test_ensemble_store.py \
  python/hearttwin/tests/test_provenance_mapping.py
45 passed, 6 warnings
```

The temporary-store API probe passed exact ensemble/trial readback and all three metric delta checks. The selected frontend contract run produced **23 passing tests**; one scenario test was blocked by the existing Node strip-only harness rejecting a TypeScript parameter property in the imported playback module. Existing direct TypeScript, scoped lint, and Next build evidence is recorded separately in the M10/M10.5 release ledger.

## Findings and release impact

1. **PASS:** EF, SV, and CO are numerically continuous from the canonical Python output through typed state, API payload, temporary persistence, Shadow Trial pair, and comparison display model.
2. **PASS:** Scenario deltas are carried as backend/domain values and are not recomputed by the comparison display layer.
3. **PASS:** The exercised provenance identifiers and version metadata survive API persistence and frontend ensemble/comparison projections.
4. **OPEN:** The unified REPORT mode does not display representative numerical values or detailed provenance; it only reports section readiness and source IDs. If “report values” means a full numerical release report, this is a release-surface gap.
5. **OPEN:** No supported-browser visual verification was possible in this audit, so the final DOM/rendered-value path remains unproven.
6. **OPEN:** External persistence, backup/restore, public deployment, authentication, and patient-data suitability remain outside this local synthetic wiring result.

**Agent 20 verdict: PASS for local computational wiring; M10.5 release gate remains OPEN because the unified report and browser/deployment boundaries are not fully verified.**
