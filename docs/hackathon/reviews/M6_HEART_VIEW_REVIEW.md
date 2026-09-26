# M6 Heart View Review

**Agent:** M6 agent #19  
**Scope:** one-heart visualization boundary for the M6 Shadow Trial surface  
**Date:** 2026-09-26  
**Verdict:** **PASS — boundary preserved**

This is a read-only review. No production code was changed.

## Evidence

| Boundary | Evidence | Finding |
| --- | --- | --- |
| One 3D heart | `web/components/layout/AppShell.tsx:157-160` mounts one `HeartScene`. `web/components/heart/HeartScene.tsx:884-913` mounts one `Canvas`; `:817` adds one `HeartBody` to the scene. | M6 retains one 3D heart viewport. There is no second canvas, second heart body, or split-heart composition. |
| M6 paired inspection | `web/components/twin/shadow-trial/ShadowTrialPanel.tsx:53-75` renders baseline/scenario scalar values and pair identity. `:137` explicitly states that pointwise PV uncertainty is unavailable and is not fabricated. | Shadow Trial comparison stays in the distribution and scalar inspection surface; it does not add a second 3D heart. |
| Hypothetical labeling | `web/components/twin/scenario/ScenarioPanel.tsx:24-26` labels the M4 surface `HYPOTHETICAL SIMULATION`. `web/components/twin/shadow-trial/ShadowTrialPanel.tsx:125-127,139` labels the M6 surface `PAIRED HYPOTHETICAL EXPERIMENT` and retains the non-clinical boundary. `web/components/heart/HeartScene.tsx:1008` labels a selected ensemble sample as `PLAUSIBLE SIMULATED TWIN`. | Scenario, plausible-twin, and Shadow Trial states are visibly distinguished from observed/live state. |
| M4 visual helpers | `web/lib/twin/scenario/heart.ts:4-26` describes visual binding and explicitly does not claim geometric measurements. `web/lib/twin/scenario/visualization.ts:10-52` maps scenario state into existing visual channels and labels it hypothetical. `web/lib/twin/ensemble/visualization.ts:9-25` calls the M5 path a scalar projection and holds the baseline PV shape. | Existing M4/M5 helpers remain bounded presentation projections; they do not introduce a new anatomical model or a second heart. |
| Canonical numerical authority | `web/components/heart/HeartScene.tsx:952-961` selects stored observed, ensemble, or scenario state and visualization inputs. `:1021-1030` passes those inputs into the single canvas. The reviewed heart and Shadow Trial paths contain no model-provider or LLM call. | The view consumes canonical state supplied by the backend/active scenario path. It does not generate canonical physiology values in the UI. Visual animation and scalar mapping remain presentation behavior. |
| M7/M8 boundary | The inspected active paths contain no Split Heart viewport and no Missing Piece surface. The M6 panel is mounted below the existing scenario surface (`ScenarioPanel.tsx:52-54`) and only adds paired scalar inspection. | M7 Split Heart and M8 Missing Piece UI were not introduced or started by this task. |

## Review conclusions

1. M6 continues to show exactly one procedural 3D heart.
2. A Shadow Trial pair is represented by backend-returned distributions, pair IDs,
   and baseline/scenario scalar values; it is not rendered as two hearts.
3. Hypothetical and simulated labels are present at the M4, M5, M6, and viewport
   boundaries, including the non-clinical warning.
4. The reviewed UI does not call a model provider or invent canonical cardiac
   measurements. Existing helper transformations are explicitly visual/scalar
   projections and preserve the PV-shape limitation.
5. No M7 Split Heart or M8 Missing Piece implementation is included.

## Validation

- Source inspection covered the active `HeartScene`, `AppShell`, M4 scenario
  helpers, M5 scalar visualization helper, and M6 Shadow Trial panel.
- A targeted search found no Split Heart/Missing Piece UI or model-provider call
  in those paths.
- Documentation-only change; no frontend or backend test run was necessary.

