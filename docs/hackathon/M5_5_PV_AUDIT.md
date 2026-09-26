# M5.5 PV Uncertainty Audit

Date: 2026-09-26  
Scope: active plausible-twin backend contract and frontend PV/uncertainty
surfaces. Read-only audit; no M6, M7, or M8 work.

## Verdict

**PASS for the requested honesty boundary.** The active M5.5 ensemble path
does not fabricate a pointwise pressure-volume uncertainty envelope from scalar
percentiles. It exposes scalar EF/SV uncertainty, labels the limitation, and
holds the baseline PV shape when a sampled twin is selected.

No production code change was required.

## Backend data actually available

The ensemble response contract defines four output metric IDs only:
`ejection_fraction_pct`, `stroke_volume_ml`, `cardiac_output_l_min`, and
`heart_rate_bpm` ([`python/hearttwin/ensemble.py:118-123`](../../python/hearttwin/ensemble.py#L118-L123)).
Each metric has scalar samples, summary statistics, and q05/q25/q75/q95
quantiles ([`python/hearttwin/ensemble.py:137-151`](../../python/hearttwin/ensemble.py#L137-L151)).
The sample contract contains sampled parameters, scalar outputs, and a typed
state; it has no PV-loop trajectory field
([`python/hearttwin/ensemble.py:188-202`](../../python/hearttwin/ensemble.py#L188-L202)).

The API runs and persists this ensemble response at
`POST /api/v1/twin/ensemble`; it does not add visualization PV data
([`python/hearttwin/api.py:156-168`](../../python/hearttwin/api.py#L156-L168)).
The frontend wire type matches that shape: `distributions` and `samples` are
present, but neither the response nor sample types contain `pv_loop`,
`pointwise_pv`, or an envelope
([`web/types/ensemble.ts:33-85`](../../web/types/ensemble.ts#L33-L85)).

Independent execution of the canonical backend with
`fixtures/golden/probabilistic/fixed-only.json` produced:

```text
response_keys = accepted_sample_count, distributions, id,
                 origin_snapshot_id, parameter_distributions, provenance,
                 rejected_sample_count, representative_sample_ids,
                 requested_sample_count, safety_disclaimer, samples, seed,
                 warnings
metric_ids = ejection_fraction_pct, stroke_volume_ml,
             cardiac_output_l_min, heart_rate_bpm
has_pointwise_pv = False
has_pv_in_sample = False
```

The backend does produce a deterministic PV curve for the ordinary operation
visualization payload, including `volume_ml` and `pressure_mmhg`
([`python/hearttwin/agents/hemodynamics_agent.py:672-685`](../../python/hearttwin/agents/hemodynamics_agent.py#L672-L685)).
That is a separate single-visualization channel, not pointwise PV data for the
M5.5 ensemble samples.

## Active frontend behavior

- The active ensemble request sends distributions and the seed to the backend;
  it does not sample or evaluate physiology in the browser
  ([`web/lib/twin/ensemble/backend.ts:13-68`](../../web/lib/twin/ensemble/backend.ts#L13-L68)).
- The adapter maps backend samples and distributions without recomputing
  metrics ([`web/lib/twin/ensemble/adapter.ts:5-64`](../../web/lib/twin/ensemble/adapter.ts#L5-L64)).
- `pvUncertaintyEnvelope` returns scalar EF/SV distributions and hard-codes
  `pointwiseLoopAvailable: false`; its limitation explicitly says pointwise PV
  uncertainty is unavailable
  ([`web/lib/twin/ensemble/pvEnvelope.ts:3-23`](../../web/lib/twin/ensemble/pvEnvelope.ts#L3-L23)).
- The plausible-twins panel renders “Scalar EF/SV uncertainty” and the q05–q95
  ranges, not a curve band. It also states “baseline PV shape held” and labels
  the result as a plausible simulated twin
  ([`web/components/twin/ensemble/PlausibleTwinsPanel.tsx:98-117`](../../web/components/twin/ensemble/PlausibleTwinsPanel.tsx#L98-L117)).
- Selecting a sample projects scalar values into existing visual channels but
  copies the baseline `pv_loop` unchanged and marks it “baseline PV shape held”
  ([`web/lib/twin/ensemble/visualization.ts:9-25`](../../web/lib/twin/ensemble/visualization.ts#L9-L25)).
- The component inspector likewise calls its values “mapped scalar outputs” and
  explicitly disclaims a geometric or clinical confidence estimate
  ([`web/components/twin/ensemble/EnsembleUncertaintyInspector.tsx:22-37`](../../web/components/twin/ensemble/EnsembleUncertaintyInspector.tsx#L22-L37)).

The ordinary Plotly PV chart draws one supplied curve and, when comparing an
M4 scenario, an observed-baseline dotted curve; it does not draw an ensemble
pointwise band ([`web/components/charts/SimulationCharts.tsx:180-214`](../../web/components/charts/SimulationCharts.tsx#L180-L214)).
The recovery chart's shaded bands are cardiac-output trajectory bands, not PV
uncertainty ([`web/components/charts/SimulationCharts.tsx:303-335`](../../web/components/charts/SimulationCharts.tsx#L303-L335)).

## Verification

Passed:

```text
PYTHONPATH=. uv run --project . --extra dev pytest -q \
  python/hearttwin/tests/test_ensemble.py \
  python/hearttwin/tests/test_ensemble_api.py \
  python/hearttwin/tests/test_probabilistic_golden.py \
  python/hearttwin/tests/test_ensemble_store.py
39 passed

cd web && npm run test:runtime
2 passed

cd web && npx tsc --noEmit
passed with no output
```

The runtime harness specifically asserts that the mapped backend ensemble has
`pointwiseLoopAvailable === false`
([`web/tests/m5-runtime.test.ts:48-100`](../../web/tests/m5-runtime.test.ts#L48-L100)).

## Boundary and follow-up

Pointwise PV uncertainty must remain unavailable until the backend versioned
ensemble contract returns a PV trajectory for every accepted sample, with a
defined alignment/sampling policy and provenance. Scalar EF/SV percentiles must
not be converted into pressure or volume coordinates, and a baseline PV shape
must not be presented as an uncertainty envelope.

This audit does not start M6, M7, or M8.
