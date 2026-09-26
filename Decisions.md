# BeatIT Decisions

Last updated: 2026-09-26

## Product identity

- The application is branded **BeatIT**.
- **DualBeat** remains the underlying engine and research lineage where that name is useful.

## Physiology and scenario modeling

- The canonical cardiac calculations are deterministic and auditable; AI/model integrations may explain or enrich results but do not silently alter the core physiology.
- The observed twin snapshot is treated as immutable. Hypothetical scenarios are isolated from it, retain their origin snapshot identity and timestamp, and are deep-frozen at the model boundary.
- M4 exposes five controlled parameters: heart rate, preload, afterload, contractility, and systemic vascular resistance. Shared validation and explicit bounds are required.
- Scenario timestamps derive from the origin snapshot so repeated runs are deterministic.
- Pressure-volume curves, ECG changes, and 3D heart changes are educational visual projections, not claims of patient-specific geometric prediction.
- Hypothetical states must remain visibly labeled and must not be presented as diagnosis or treatment advice.
- M5 uncertainty is introduced only through validated input distributions; the deterministic physiology engine is not made noisy.
- M5 percentiles are descriptive summaries of accepted deterministic simulations, not clinical confidence intervals, credible intervals, or patient probabilities.
- Invalid sampled inputs are rejected with reasons rather than silently clamped. Until a validated joint model exists, parameter independence is an explicit assumption.

## Local model strategy

- Local storage is searched and audited before any model acquisition; no model downloads are performed without an explicit decision.
- The existing VISTA-3D checkpoint is reused through an optional, lazy adapter. Procedural behavior remains the safe fallback when the adapter cannot run.
- Language-model integration remains provider-neutral, with a deterministic fallback. The locally inventoried language models are not activated by default.
- Embedding, ECG, and OCR models are not added without a demonstrated product gap and a validated local artifact.
- Model weights stay outside the repository. The registry is lazy and the status endpoint must be safe when models or checkpoints are unavailable.

## Engineering and delivery

- Existing provider-neutral intelligence and storage interfaces are preserved.
- GitHub Actions and other CI/CD changes are out of scope unless explicitly requested.
- Completion is reported against evidence and gates; incomplete work is not represented as complete.
- The M4 agent ledger records actual dispatches and meaningful contributions rather than inflating the count.
- Frontend and Python ensemble engines are currently separate versioned implementations; cross-layer golden-vector parity is required before treating them as equivalent.
- Process-local ensemble retrieval is acceptable for the hackathon surface but is not durable persistence or multi-worker storage.

## M5.5 closure decisions

- Python `m5.5-ensemble-projection-v1` is the sole active authority for ensemble sampling, validity, physiology projection, statistics, identifiers, provenance, and safety disclaimer output. The separate frontend runner is retained only for historical tests and is not imported by the active scenario flow.
- The wire contract is snake_case and versioned as `m5.5-backend-ensemble-v1`; the frontend maps it without recomputing numeric outputs.
- Local ensemble persistence uses file-backed SQLite by default (`BEATIT_ENSEMBLE_DB_PATH`). Non-durable in-memory ensemble storage is not an implicit fallback.
- Ensemble requests require explicit `origin_quality` and preserve replay provenance/evidence IDs. Synthetic replay cannot be labeled observed when replay provenance is supplied.
- PV uncertainty is intentionally bounded to scalar EF/SV summaries until the backend returns pointwise loop samples. The UI must state that the baseline PV shape is held and must not fabricate a curve envelope.
- M5.5 remains incomplete until browser/accessibility QA and remaining credibility gates have evidence. M6 is not started.
