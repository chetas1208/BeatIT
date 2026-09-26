# M5 Agent Plan

M5 requires at least 20 completed, meaningful, reviewed contributions. Agent
dispatches and outcomes are recorded here as work completes; names alone do
not satisfy the gate.

## Workstreams

1. M4 dependency closure
2. Uncertainty taxonomy
3. Evidence mapping
4. Distribution validation
5. Prior construction
6. Evidence conditioning
7. Seeded sampling
8. Correlation assumptions
9. Physiological validity
10. Ensemble execution
11. Parallel execution
12. Statistics
13. Synthetic calibration
14. Provenance
15. API
16. Distribution visualization
17. Heart uncertainty projection
18. Representative twin explorer
19. Component uncertainty inspection
20. Uncertainty reporting
21. PV envelope
22. Temporal freshness policy
23. Scenario compatibility
24. Performance benchmarking
25. Statistical integrity review
26. Cardiac modeling review
27. Architecture review
28. Hackathon UX review

## Completion rule

Only a returned contribution that was inspected by the lead and either
integrated, converted into a documented decision, or recorded as a reviewed
blocker counts toward the meaningful total.

## Actual contribution ledger

Reviewed against the current source tree and M5 artifacts on 2026-09-26. The
campaign has now returned **22 meaningful, reviewed contributions**, satisfying
the agent-count gate. The technical milestone remains incomplete because the
other release gates are still open.

## Completed sub-agent contributions

| # | Agent output | Evidence or integration |
|---:|---|---|
| 1 | Hegel — M4 readiness audit | M4 closure findings integrated into `M4_CLOSURE.md`. |
| 2 | Dalton — uncertainty taxonomy | `web/types/uncertainty.ts` and `M5_UNCERTAINTY_MODEL.md`. |
| 3 | Meitner — evidence mapping audit | Parameter/evidence exclusions integrated into priors and provenance decisions. |
| 4 | Arendt — distribution tests | `distributions.test.ts`; TypeScript and focused lint passed. |
| 5 | Boyle — statistics tests | `statistics.test.ts`; TypeScript and focused lint passed. |
| 6 | Ohm — Python ensemble tests | `test_ensemble.py`; 12 passed. |
| 7 | Poincare — benchmark implementation | `scripts/benchmark_ensemble.py`; required sample counts executed. |
| 8 | Pauli — M4/M5 scenario compatibility audit | Scenario adapter and M6 boundary documented/integrated. |
| 9 | Cicero — statistics integrity audit | Quantile convention and numeric-risk findings reviewed. |
| 10 | Laplace — provenance audit | Version, identity, evidence, and immutability fixes reviewed/integrated. |
| 11 | Descartes — UX/accessibility audit | Simulated/live labeling, selected state, and warning disclosure fixed. |
| 12 | Schrodinger — API route audit | Create/get/distribution route behavior reviewed. |
| 13 | Boole — evidence-source audit | Proxy labels and field-relevant evidence handling corrected. |
| 14 | Pascal — scientific-language audit | Completion and percentile wording reviewed. |
| 15 | Pasteur — API tests | `test_ensemble_api.py`; 5 passed. |
| 16 | Confucius — provenance tests | `provenance.test.ts`; TypeScript and focused lint passed. |
| 17 | Volta — agent ledger maintenance | This ledger updated and reviewed. |
| 18 | Herschel — frontend regression audit | TypeScript/lint/build pass; alias-based runtime test blocker recorded. |
| 19 | Hypatia — Python regression audit | 137 focused regression tests passed. |
| 20 | Avicenna — cross-layer parity audit | Formula, PRNG, rounding, and validation divergences documented. |
| 21 | Kuhn — benchmark integrity audit | Non-reproducible single-run timings downgraded to smoke evidence. |
| 22 | Socrates — release-gate audit | Root and M5 status records tightened; remaining blockers retained. |

Each contribution was inspected by the lead. A stopped medical-integrity
reviewer and an interrupted runner-test attempt are not counted.

| WS | Reviewed output | Integration result |
|---:|---|---|
| 2 | `M5_UNCERTAINTY_MODEL.md`, `web/types/uncertainty.ts` | Docs and frontend contracts integrated; backend-wide uncertainty record integration is not claimed. |
| 3 | `M5_PRIORS.md`, `web/lib/twin/ensemble/runner.ts` | Evidence IDs and relevance filtering integrated in the frontend prior builder; Python provenance remains partial. |
| 4 | `M5_PARAMETER_DISTRIBUTIONS.md`, `web/lib/twin/ensemble/distributions.ts`, `python/hearttwin/ensemble.py` | Distribution families, bounds, and validation integrated in both implementations with focused tests. |
| 5 | `M5_PRIORS.md`, `python/hearttwin/data/priors.json`, frontend default distributions | Versioned bounded priors integrated in the frontend/docs; a complete shared backend prior-construction path is not claimed. |
| 6 | `M5_PRIORS.md`, `web/lib/twin/ensemble/runner.ts` | Evidence-conditioned frontend distribution selection integrated; cross-layer parity remains open. |
| 7 | `M5_SAMPLING.md`, seeded runners, ensemble tests | Seeded deterministic sampling integrated in frontend and backend with replay tests. |
| 8 | `M5_SAMPLING.md`, `M5_DECISIONS.md`, ensemble provenance | Independent-parameter assumption is documented and retained in output provenance; validated correlations are not implemented. |
| 9 | `M5_SAMPLING.md`, validity checks, ensemble tests | Bounds, rejection reasons, and physiological invariants integrated in frontend and backend. |
| 10 | `M5_ARCHITECTURE.md`, ensemble runners | Deterministic ensemble execution integrated in frontend and backend; the implementations are not yet one shared engine. |
| 12 | `M5_SAMPLING.md`, statistics modules, statistics tests | Mean, variance, standard deviation, empirical quantiles, and ranges integrated with focused tests. |
| 14 | `M5_DECISIONS.md`, ensemble provenance, provenance tests | Seed, origin, engine/config/prior versions, evidence, and assumptions are retained; backend fields remain less complete than frontend fields. |
| 15 | `python/hearttwin/api.py`, `python/hearttwin/tests/test_ensemble_api.py` | FastAPI create/get/distribution routes integrated and route-tested; storage is intentionally process-local. |
| 16 | `PlausibleTwinsPanel.tsx`, ensemble visualization contracts | Percentile summaries and distribution presentation integrated into the scenario UI; browser QA is still outstanding. |
| 17 | scenario ensemble state and selected-sample projection | Selected valid samples can drive the scenario/heart projection path; visual and accessibility validation is not complete. |
| 18 | `PlausibleTwinsPanel.tsx`, representative-selection tests | Low, median-nearest, and high accepted representatives are integrated and tested. |
| 20 | `M5_UNCERTAINTY_MODEL.md`, `PlausibleTwinsPanel.tsx`, output warnings | Simulation uncertainty is reported with explicit educational/non-clinical labeling; full cross-layer reporting parity is not claimed. |

### Reviewed but not counted as completed

| WS | Reviewed output | Reason not counted |
|---:|---|---|
| 1 | `M5_ARCHITECTURE.md` and both ensemble implementations | M4 dependency closure is not complete because frontend/backend physiology parity remains an explicit release risk. |
| 11 | `M5_ARCHITECTURE.md` and ensemble runners | No parallel execution implementation or review evidence was found; execution is sequential. |
| 13 | M5 completion and performance records | No synthetic calibration implementation or validation evidence was found. |
| 19 | heart component registry and uncertainty UI files | Component uncertainty inspection remains reserved/future rather than integrated. |
| 21 | existing `web/lib/twin/scenario/pv.ts` and M5 completion record | No M5 PV-envelope output or integration was found; the existing PV helper is a prior scenario projection, not an ensemble envelope. |
