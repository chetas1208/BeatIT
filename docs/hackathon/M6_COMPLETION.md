# M6 Completion Record — Shadow Trial Engine

Last updated: 2026-09-26.

## Status

**INCOMPLETE — NOT READY FOR M7.** The paired backend engine, immutable local
trial persistence, API routes, focused UI, golden fixtures, and review ledger
are present. Core automated gates pass; browser/accessibility, hosted security,
full persisted-baseline benchmark restart coverage, and bounded provenance/MAP
review findings remain open. No M7 or M8 work is included.

## Delivered

- A versioned backend `ScenarioDefinition` and `ShadowTrialDefinition` contract
  with explicit scenario bounds, units, provenance, fingerprints, and safety
  disclaimer.
- Same-sample pairing over one persisted M5.5 ensemble. Each scenario twin
  keeps the baseline sample ID, reuses the stored parameter vector, and applies
  only requested scenario values. No M6 resampling occurs.
- M5.5 samples now retain the exact projection base used by the canonical
  Python evaluator. M6 refuses legacy samples without that base rather than
  double-applying uncertainty.
- Raw scenario-minus-baseline deltas with metric units, descriptive
  positive/near-zero/negative categories, explicit tolerances, percentiles,
  invalid-pair retention, and zero-valid failure semantics.
- Create-once, restart-safe SQLite trial storage. Exact replay is idempotent;
  conflicting payloads for an existing trial ID are rejected.
- `POST /api/v1/shadow-trials`, `GET /api/v1/shadow-trials/{trial_id}`,
  `/effects`, and `/pairs/{sample_id}` routes.
- A focused frontend experiment panel with distribution summaries, pair
  inspection, failed/empty states, one-heart scope, scalar PV boundary, and
  synthetic/hypothetical labeling. It does not calculate canonical math.
- Synthetic golden Shadow Trial fixtures plus an exact numerical
  fixed-baseline vector.

## Evidence collected

- Focused M6 Python/API/store/golden/reproducibility suite: **40 passed**.
- Full Python 3.13 suite after M6 additions: **979 passed, 1 skipped**.
- API tests cover creation, retrieval, effects, pair inspection, missing
  resources, invalid bounds, idempotency, safety disclaimer, and persistence
  failure mapping.
- Golden tests cover the canonical evaluator, fixed baseline, invalid pairs,
  identity/no-op, reproducibility, and mixed-sample projection-base behavior.
- Frontend TypeScript and alias-aware runtime suite: **5 passed**.
- Frontend production build passed; lint has **0 errors and 2 existing image
  warnings**.
- M6 agent plan records actual dispatches and reviewed contributions. A review
  counts only when its file and evidence were inspected by the lead.

## Open gates and risks

- Browser interaction, responsive, keyboard, screen-reader, and visual QA are
  not claimed until a browser can launch. M5.5's Chromium run was blocked by a
  missing `libasound.so.2`; direct HTTP 200 is not browser evidence.
- Existing synthetic/demo security limits remain: unauthenticated routes,
  permissive CORS, and full-state local persistence are not suitable for
  patient-data deployment.
- The benchmark review confirms deterministic local measurements but does not
  yet prove the complete persisted-baseline/subprocess benchmark envelope.
- Provenance is conditionally adequate for the demo; execution timestamps,
  stronger version/hash binding, and complete stage-specific lineage remain
  bounded follow-up work.
- Pointwise PV loop uncertainty is unavailable; M6 does not fabricate it.
- M6 effect categories are simulation direction labels, never benefit/harm,
  treatment, efficacy, diagnosis, or patient probability claims.
- Thirty-six counted substantive reviewed contributions are evidenced in
  `M6_AGENT_PLAN.md`; the requested 20-agent gate is met with 36 counted
  substantive contributions. Overlapping dispatches remain explicitly
  uncounted.

## M7/M8 boundary

M7 Split Heart, M8 Missing Piece, sensitivity/information-gain ranking,
clinical calibration, treatment ranking, and final product redesign remain
explicitly out of scope.

## Readiness decision

Current decision: **NOT READY FOR M7** until the open validation and browser /
accessibility gates are either passed or deliberately accepted by the project
owner. If those gates close without regressions, this record may be updated to
`READY FOR M7` in a separate review; no M7 implementation should be inferred
from this M6 work.
