# M7 Agent Plan — Split Heart

Status: `IN_PROGRESS`

This ledger records only substantive contributions that are completed, reviewed,
and either integrated or intentionally rejected. Dispatch alone does not satisfy
the M7 contribution gate. The lead owns final integration and the final gate.

| ID | Responsibility | Owned paths | Dependencies | Expected deliverable | Started | Completed | Reviewed | Integrated | Rejected | Reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | M6 pairing audit | `docs/hackathon/M7_PAIRING_AUDIT.md` | M6 result contracts | Pair identity audit | 2026-09-26 | 2026-09-26 | lead | yes |  | Conditional pass; baseline immutability caveat documented |
| 02 | Split-heart scene architecture | `docs/hackathon/M7_ARCHITECTURE.md` | Existing HeartScene | Layout/instance design | 2026-09-26 | 2026-09-26 | lead | yes |  | Documents two injected instances and procedural limit |
| 03 | Heart instance isolation | `web/lib/twin/comparison/isolation.ts`, tests | Heart interaction hooks | Isolation contract/tests |  |  |  |  |  |  |
| 04 | Comparison clock architecture | `web/lib/twin/comparison/contracts.ts` | M1 clock, M7 contracts | Clock contract | 2026-09-26 | 2026-09-26 | lead | yes |  | 7 focused clock tests passed |
| 05 | Phase-locked clock review | `web/lib/twin/comparison/__tests__/phase-lock.test.ts` | Clock contract | Phase-lock tests | 2026-09-26 | 2026-09-26 | lead | yes |  | Existing focused tests passed |
| 06 | Physiologic-rate review | `web/lib/twin/comparison/__tests__/physiologic-rate.test.ts` | Clock contract | True-rate tests | 2026-09-26 | 2026-09-26 | lead | yes |  | Existing focused tests passed |
| 07 | Split transition design | `docs/hackathon/M7_SPLIT_HEART.md` | Scene architecture | Motion/reduced-motion spec | 2026-09-26 | 2026-09-26 | lead | yes |  | Runtime transition caveat documented |
| 08 | Camera behavior review | `docs/hackathon/M7_CAMERA_REVIEW.md` | Heart scene | Camera safety constraints | 2026-09-26 | 2026-09-26 | lead | yes |  | Active UI camera linkage remains open |
| 09 | Semantic selection mapping | `web/lib/twin/comparison/selection.ts`, tests | M2 registry | Linked selection mapping | 2026-09-26 | 2026-09-26 | lead | yes |  | 31 comparison tests passed in agent report |
| 10 | Difference engine | `web/lib/twin/comparison/differences.ts`, tests | M6 pair DTO | Deterministic delta mapping |  |  |  |  |  |  |
| 11 | Difference-only semantics | `docs/hackathon/M7_DIFFERENCE_ENGINE.md` | Difference engine | Threshold/display policy |  |  |  |  |  |  |
| 12 | Component inspector | `web/lib/twin/comparison/inspector.ts`, tests | Difference engine | Component comparison model |  |  |  |  |  |  |
| 13 | PV comparison | `web/lib/twin/comparison/pv.ts`, tests | Clock contract | Cursor projection | 2026-09-26 | 2026-09-26 | lead | yes |  | Cursor/uncertainty boundary tests passed |
| 14 | PV synchronization audit | `docs/hackathon/M7_CLOCK_MODES.md` | PV projection | Timing audit | 2026-09-26 | 2026-09-26 | lead | yes |  | Single RAF and phase semantics documented |
| 15 | ECG/signal boundary | `docs/hackathon/M7_SIGNAL_BOUNDARY.md` | Existing ECG types | Honest signal policy | 2026-09-26 | 2026-09-26 | lead | yes |  | No measured waveform fabrication |
| 16 | Hemodynamic comparison | `web/lib/twin/comparison/metrics.ts`, tests | M6 deltas | Supported metric model |  |  |  |  |  |  |
| 17 | Contraction projection | `docs/hackathon/M7_CONTRACTION_BOUNDARY.md` | 3D projection | Non-FE limitation |  |  |  |  |  |  |
| 18 | AHA-17 mapping | `web/lib/twin/comparison/regions.ts`, tests | M2 registry | Defensible region mapping |  |  |  |  |  |  |
| 19 | Coronary mapping audit | `docs/hackathon/M7_CORONARY_AUDIT.md` | Registry/findings | Supported/unsupported mapping |  |  |  |  |  |  |
| 20 | Electrical comparison | `docs/hackathon/M7_ELECTRICAL_BOUNDARY.md` | Existing electrical layer | Educational boundary |  |  |  |  |  |  |
| 21 | Central metrics | `web/components/twin/comparison/ComparisonMetrics.tsx` | Metrics model | Compact comparison table | 2026-09-26 | 2026-09-26 | lead | yes |  | Accessible table and explicit EF units |
| 22 | Pair explorer | `web/components/twin/comparison/PairExplorer.tsx` | M6 pairs | Representative pair selection |  |  |  |  |  |  |
| 23 | Uncertainty comparison | `docs/hackathon/M7_UNCERTAINTY.md` | M5.5 scalar boundary | Honest uncertainty display |  |  |  |  |  |  |
| 24 | Provenance view | `web/lib/twin/comparison/provenance.ts`, tests | M6 provenance | Causal trace projection | 2026-09-26 | 2026-09-26 | lead | yes |  | 5 provenance tests passed |
| 25 | Deterministic report | `web/lib/twin/comparison/report.ts`, tests | Comparison model | Exportable report data |  |  |  |  |  |  |
| 26 | Local model boundary | `docs/hackathon/M7_MODEL_BOUNDARY.md` | Assistant interfaces | Explanation-only policy |  |  |  |  |  |  |
| 27 | Comparison persistence | `web/lib/twin/comparison/persistence.ts`, tests | UI state | Non-canonical UI persistence |  |  |  |  |  |  |
| 28 | Performance review | `docs/hackathon/M7_PERFORMANCE.md` | Dual scene | Measurement plan/results |  |  |  |  |  |  |
| 29 | Browser QA | `docs/hackathon/M7_BROWSER_QA.md` | Integrated UI | Actual flow evidence |  |  |  |  |  |  |
| 30 | Accessibility review | `docs/hackathon/M7_ACCESSIBILITY.md` | Integrated UI | Keyboard/motion audit |  |  |  |  |  |  |
| 31 | Visual architecture review | `docs/hackathon/reviews/M7_VISUAL_ARCHITECTURE.md` | Feature freeze | Adversarial findings |  |  |  |  |  |  |
| 32 | Cardiac integrity review | `docs/hackathon/reviews/M7_CARDIAC_INTEGRITY.md` | Feature freeze | Physiology integrity findings |  |  |  |  |  |  |
| 33 | Statistical review | `docs/hackathon/reviews/M7_STATISTICS.md` | Feature freeze | Pair/uncertainty language review |  |  |  |  |  |  |
| 34 | Demo narrative review | `docs/hackathon/reviews/M7_DEMO_NARRATIVE.md` | Feature freeze | Five-second comprehension review |  |  |  |  |  |  |

## Contribution gate

The M7 gate requires at least 20 rows with evidence of a meaningful completed
contribution, lead review, and integration or explicit rejection. Rows are not
counted merely because an agent was dispatched or named.

Current evidence-backed count: **10** completed, reviewed, non-duplicative
contributions. Additional unverified artifacts in the shared worktree are not
counted until their agent completion and review evidence is available.

## Ownership rules

- Agents may edit only their owned paths.
- Shared integration files (`web/components/heart/HeartScene.tsx`,
  `web/components/layout/AppShell.tsx`, `Decisions.md`, and `Progress.md`) are
  lead-owned unless explicitly reassigned.
- The lead reviews every submitted artifact against the M6 numerical contracts.
