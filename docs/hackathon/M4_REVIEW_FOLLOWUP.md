# M4 adversarial follow-up

Follow-up date: 2026-09-26 UTC. This records lead integration changes after
the independent architecture review in `M4_REVIEW_ARCHITECTURE.md`.

| Finding | Follow-up |
|---|---|
| JSX provider extension | Fixed by moving the provider to `useScenario.tsx`; direct typecheck and focused lint pass. |
| Projection seam disconnected | Fixed with `ScenarioProvider` and `scenarioVisualization`; HeartScene and SimulationCharts now consume the hypothetical projection while keeping the observed PV trace as a subdued reference. |
| Parameter validation mismatch | Fixed at `propagateScenario` boundary: unknown/out-of-range/duplicate inputs raise `RangeError`; evaluation uses shared definitions. |
| Incorrect graph topology | Fixed by rendering returned causal paths and graph-derived labels rather than array adjacency. |
| Runtime immutability/history | Scenario origin/result are deeply frozen; undo/redo restores the control values represented by the present result. Persistence remains versioned and optional. |

Remaining acceptance gates are the browser manual demo, full production lint
cleanup outside M4, and the runtime's inability to provide 20 concurrent
subagent threads in one batch. No clinical claim is made.
