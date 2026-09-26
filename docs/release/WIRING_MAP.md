# BeatIT M10.5 Wiring Map

This map describes the exercised authority path for the frozen product. It
does not claim browser completion where the current host cannot launch a
supported browser.

| Capability/value | Frontend | API | Domain authority | Persistence/source | Verification |
|---|---|---|---|---|---|
| Baseline EF/SV/CO/MAP | Twin/report view models | `/api/v1/cases/{id}/operate`, `/api/v1/system-check` | `cardiac_state.py`, `hemodynamics.py` | Synthetic vitals and case state | numerical agent + case E2E |
| Temporal twin | Twin mode and timeline contracts | case create/extract/detail | `CardiacTwinState`, event/replay contracts | case store and synthetic replay fixtures | route/runtime audits |
| Semantic heart | `HeartScene` and anatomy bindings | operation visualization `cardiac_findings` | deterministic findings/AHA mapping | state source map and fixture metadata | numerical/source audits |
| Causal experiment | Experiment mode/scenario panel | scenario authority and existing M4 contracts | bounded scenario propagation | scenario lineage/provenance | product/API tests |
| Probabilistic twin | ensemble panel and adapters | `/api/v1/twin/ensemble` plus retrieval | `ensemble.py` seeded sampler | SQLite ensemble store | API E2E, reproducibility |
| Shadow Trial | experiment/compare adapters | `/api/v1/shadow-trials` and pair/effects routes | same-sample paired engine | SQLite Shadow Trial store | pair/idempotence E2E |
| Split Heart | Compare mode and comparison inspectors | persisted M6 pair response | backend-authoritative deltas | Shadow Trial lineage | frontend/source audit; browser open |
| Missing Piece | Evidence mode selectors and cards | `/api/v1/missing-piece` and retrieval | bounded M8 sensitivity/evidence engine | SQLite Missing Piece store | model-disabled API E2E |
| Report | Report mode contract/composition | case, ensemble, trial, analysis reads | report contract preserves unavailable sections | persisted artifact lineage | frontend/runtime audit |
| Provenance | source-status badges, inspectors, report fields | disclaimer and provenance payloads | canonical provenance mapping | source maps, fixture manifests | numerical/scientific audits |
| Optional language model | Copilot route and assistant states | model/intelligence status | explanation/extraction only | provider config; no numerical authority | placeholder config; fallback E2E |
| Optional VISTA-3D | procedural heart fallback | model status / imaging adapters | optional segmentation adapter | checkpoint outside repository | disabled/fallback evidence |
| Demo data | preflight and demo product context | synthetic case/fixture APIs | deterministic core | `data/manifest.json`, release golden manifest | seed/reset/verify |
| Local persistence | UI reload consumers | retrieval routes | typed stores | SQLite/filesystem | separate-process E2E |
| Deployment | Next.js app under `web/` | FastAPI loopback process | launcher/reverse proxy boundary | `.run/beatit` PIDs and logs | alternate-port lifecycle |

## Authority rule

Frontend code composes and labels backend results. It does not recalculate
physiology, pair unrelated samples, or turn unavailable evidence into values.
The local model may explain or extract; it never becomes the numerical
authority.
