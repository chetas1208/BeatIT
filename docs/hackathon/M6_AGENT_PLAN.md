# M6 Agent Plan — Shadow Trial Engine

Last updated: 2026-09-26

Execution status: AUTHORIZED. The preflight is complete enough to proceed with
bounded repairs: M5.5's persisted Python ensemble is the baseline authority;
the unintegrated scaffold below is being consolidated, not treated as a
second authority.

## Scope

M6 adds a paired, deterministic Shadow Trial over one persisted M5.5 baseline
ensemble. Each baseline sample is transformed into its counterfactual scenario
state without resampling latent parameters. M6 reports descriptive paired
effects and preserves the individual pairs for later milestones.

M7 Split Heart, M8 Missing Piece, clinical calibration, treatment ranking,
clinical efficacy, and final product redesign are explicitly out of scope.

## Operating rules

- The Python backend remains the sole numerical authority.
- A baseline sample may only pair with the scenario result derived from that
  same sample identity.
- Baseline ensembles, snapshots, and scenario definitions are immutable inputs.
- Invalid pairs are retained with reasons and counted, never silently dropped.
- Positive/near-zero/negative are descriptive simulation categories, not clinical
  benefit or harm judgments.
- Every contribution must include substantive evidence and be reviewed by the
  lead before it counts toward the 20-contribution gate.
- Shared API, persistence, and root documentation files are integrated by the
  lead after isolated work is reviewed.

## Workstreams and ownership

| # | Agent identifier / responsibility | Primary owned files | Depends on | Expected deliverable | Status / review |
|---:|---|---|---|---|---|
| 1 | M5.5 readiness audit | `docs/hackathon/M6_PREFLIGHT.md` | none | blocker matrix and bounded go/no-go | complete / lead reviewed |
| 2 | Domain contracts | `python/hearttwin/shadow_trial_contracts.py` | 1 | one validated wire contract | scaffold present / consolidation required |
| 3 | Pair identity | `python/hearttwin/shadow_trial_identity.py`, tests | 2 | deterministic identity and order checks | scaffold present / review required |
| 4 | Scenario application seam | `python/hearttwin/shadow_trial_engine.py` | 2 | reuse M5.5 evaluator without sampling | scaffold present / canonicality repair required |
| 5 | Paired execution engine | `python/hearttwin/shadow_trial_engine.py` | 2, 4 | complete same-sample execution | scaffold present / lead integration |
| 6 | Pair validity | engine tests | 5 | retained invalid pairs and reasons | pending |
| 7 | Paired deltas | `python/hearttwin/shadow_trial_metrics.py` | 5 | unit-bearing deltas | scaffold present / review required |
| 8 | Effect statistics | metrics tests | 7 | descriptive distribution summaries | pending |
| 9 | Response categories | `docs/hackathon/M6_EFFECT_METRICS.md` | 8 | explicit sign/tolerance policy | pending |
| 10 | Trial provenance | `docs/hackathon/M6_PROVENANCE.md` | 2 | lineage and hashes | design present / integration pending |
| 11 | Trial persistence | `python/hearttwin/storage/shadow_trial_store.py` | 2 | restart-safe create-once record | scaffold present / immutability repair |
| 12 | Trial API | lead-owned `python/hearttwin/api.py` | 2, 11 | create/get/effects/pair routes | pending |
| 13 | Progress semantics | `docs/hackathon/M6_ARCHITECTURE.md` | 5, 12 | honest synchronous status contract | pending |
| 14 | Failure semantics | API tests | 11, 12 | 404/409/422/zero-valid behavior | pending |
| 15 | Frontend experiment surface | `web/components/twin/shadow-trial/` | 12 | focused experiment controls | pending |
| 16 | Effect visualization | `web/components/twin/shadow-trial/` | 8, 15 | distributions with units | pending |
| 17 | Pair inspection | `web/components/twin/shadow-trial/` | 12, 15 | baseline/scenario pair view | pending |
| 18 | PV comparison boundary | `web/lib/twin/shadowTrial/` | 15 | scalar-only honest mapping | pending |
| 19 | Heart visualization boundary | architecture doc | 15 | one-heart no-split rule | pending |
| 20 | Component inspector | frontend component | 15, 17 | bounded component readout | pending |
| 21 | Scenario presets | frontend library | 4 | declarative bounded presets | pending |
| 22 | Comparison interface | `docs/hackathon/M6_DECISIONS.md` | 15 | no M7 leakage | pending |
| 23 | Explanation grounding | backend review | 2, 8 | deterministic text boundary | pending |
| 24 | Reproducibility | trial tests | 5, 8 | same-input exact repeat | pending |
| 25 | Performance | `docs/hackathon/M6_PERFORMANCE.md` | 5, 11 | measured sample-count envelope | pending |
| 26 | Statistical integrity review | `docs/hackathon/M6_QA.md` | 5, 8 | paired-statistics audit | pending |
| 27 | Cardiac modeling review | `docs/hackathon/M6_QA.md` | 4, 7 | no formula drift audit | pending |
| 28 | Architecture review | `docs/hackathon/M6_QA.md` | 11, 12 | seam and persistence audit | pending |
| 29 | Medical language review | `docs/hackathon/M6_QA.md` | 15, 16 | safety wording audit | pending |
| 30 | Browser/UX environment audit | `docs/hackathon/M6_QA.md` | 15 | runtime evidence | pending |
| 31 | Accessibility review | `docs/hackathon/M6_QA.md` | 15, 16 | keyboard/semantic evidence | pending |
| 32 | Security/persistence review | `docs/hackathon/M6_QA.md` | 11, 12 | demo-only boundary audit | pending |

The workstream table above is the original decomposition matrix and retains
its planning statuses for traceability. The dispatch ledger and gate checklist
below are the authoritative implementation status; completed work may span
multiple matrix rows, and explicitly bounded/blocked items remain open.

## Dispatch ledger

| # | Agent ID | Responsibility | Owned files | Status | Evidence reviewed | Integration decision | Counted |
|---:|---|---|---|---|---|---|---|
| 1 | `01a0dd0d-808d-71e3-a1d3-9761354abb3f` Dirac | performance/reproducibility plan | `docs/hackathon/M6_PERFORMANCE.md` | complete | 22 focused tests, diff check | integrated | yes |
| 2 | `01a0dd0d-6f89-7f32-b4b0-ddfa53a09a54` Hypatia | immutable trial persistence | store + store tests | complete | persistence suite passed | integrated | yes |
| 3 | `01a0dd11-82e7-70c0-8496-dded4ea7111c` Newton | effect metric policy | `docs/hackathon/M6_EFFECT_METRICS.md` | complete | focused metrics tests, diff check | integrated | yes |
| 4 | `01a0dd11-90c5-75d0-abbc-31615c3186d5` Pasteur | architecture and decisions | `M6_ARCHITECTURE.md`, `M6_DECISIONS.md` | complete | diff check | integrated | yes |
| 5 | `01a0dd14-9583-7562-a71b-150dae79ff9a` Franklin | API failure semantics | `test_shadow_trial_api.py` | complete | 5 API tests | integrated | yes |
| 6 | `01a0dd14-a473-72a0-b7e2-3c055a97975e` Planck | frontend effect review | `reviews/M6_FRONTEND_EFFECT_REVIEW.md` | complete | TypeScript, diff check | integrated as fixes | yes |
| 7 | `01a0dd11-7671-7830-9931-68fd71da4351` Darwin | contract authority review | `reviews/M6_CONTRACT_REVIEW.md` | complete | 29 focused tests | integrated; projection-base repair | yes |
| 8 | `01a0dd17-186c-7371-b330-2505b3c1e14e` Boyle | one-heart boundary | `reviews/M6_HEART_VIEW_REVIEW.md` | complete | source audit, diff check | integrated | yes |
| 9 | `01a0dd17-0ae8-7fa2-b72a-fc1879e48a4a` Turing | PV boundary | `reviews/M6_PV_BOUNDARY_REVIEW.md` | complete | diff check | integrated | yes |
| 10 | `01a0dd17-0032-78e3-8339-c570a630204c` Hegel | pair inspection | `reviews/M6_PAIR_INSPECTOR_REVIEW.md` | complete | 30 tests, TypeScript | integrated as edge-state fixes | yes |
| 11 | `01a0dd19-1ff9-77f3-a8a9-1998d390f3e8` Maxwell | comparison scope | `reviews/M6_COMPARISON_SCOPE_REVIEW.md` | complete | documentation check | integrated | yes |
| 12 | `01a0dd19-1419-7a41-be92-bcc20efcc8d2` Aristotle | scenario presets | `reviews/M6_PRESET_REVIEW.md` | complete | diff check | integrated | yes |
| 13 | `01a0dd19-0941-7eb0-ac93-17801ff907d4` Euler | component inspector | `reviews/M6_COMPONENT_REVIEW.md` | complete | diff check | integrated | yes |
| 14 | `01a0dd1b-3b35-7283-8de2-3690fc70a1d4` Banach | reproducibility tests | `test_shadow_trial_reproducibility.py` | complete | 4 tests, diff check | integrated | yes |
| 15 | `01a0dd1b-2d96-7212-80c0-d3933de3e91f` Sagan | explanation grounding | `reviews/M6_EXPLANATION_GROUNDING_REVIEW.md` | complete | 32 tests, source scan | integrated | yes |
| 16 | `01a0dd1b-46bb-7f61-8063-5ef6aefaa162` Nash | statistical integrity | `reviews/M6_STATISTICAL_REVIEW.md` | complete | 27 tests, diff check | integrated; hash tolerance gap fixed | yes |
| 17 | `01a0dd1d-7fe7-7583-9efa-7658720ff8d9` Herschel | cardiac modeling | `reviews/M6_CARDIAC_MODEL_REVIEW.md` | complete | 67 focused tests | integrated | yes |
| 18 | `01a0dd1d-8c15-7791-a789-f8f62258f1ea` Mendel | architecture adversarial review | `reviews/M6_ARCHITECTURE_REVIEW.md` | complete | 36 tests, diff check | integrated; baseline gap bounded | yes |
| 19 | `01a0dd1f-92d7-7ed3-95db-9fda6e697e14` Bernoulli | medical language | `reviews/M6_MEDICAL_LANGUAGE_REVIEW.md` | complete | 40 safety/API tests | integrated | yes |
| 20 | `01a0dd21-3cbc-7b13-9630-198933eb7e68` Confucius | browser/UX environment | `reviews/M6_BROWSER_UX_REVIEW.md` | complete | direct HTTP 200/404; browser blocker recorded | integrated; browser gate remains blocked | yes |
| 21 | `01a0dd23-71db-7ea2-8f5a-38ff6b1b504b` James | accessibility review | `reviews/M6_ACCESSIBILITY_REVIEW.md` | complete | targeted ESLint, TypeScript, review | integrated; browser gate remains blocked | yes |
| 1 | `01a0dd01-52a9-7412-9913-e2058ef759e8` | deterministic pair identity | `shadow_trial_identity.py`, identity tests | reviewed | 9 focused tests and compile check passed | integrated stable pair IDs, index, and explicit identity errors | yes |
| 2 | `01a0dd01-5248-7d02-965f-ceb48b58ff0b` | domain contract design | `shadow_trial_contracts.py`, contract tests | reviewed | 3 focused contract tests passed | integrated as the single M6 wire-contract module | yes |
| 3 | `01a0dd01-5334-73b2-a421-66a0c4722393` | provenance audit | `M6_PROVENANCE.md` | reviewed | backend/frontend contract audit recorded | retained as historical audit and used to shape implemented provenance fields | yes |
| 4 | `01a0dd01-5377-7070-8c4d-93e7d8d85db1` | scenario-application audit | `reviews/M6_SCENARIO_APPLICATION_REVIEW.md` | reviewed | 150 Python tests and 2 frontend runtime tests at audit time | integrated the backend-authority and no-frontend-math boundary | yes |
| 5 | `01a0dd01-51e2-7e13-a234-9d3b1b64b583` | M6 preflight audit | `M6_PREFLIGHT.md` | reviewed | blocker matrix and scaffold test evidence | retained as preflight history; material blockers are resolved or explicitly bounded | yes |
| 6 | `01a0dd01-52f5-7d41-ab34-9bd446ce79ae` | paired execution engine | `shadow_trial_engine.py`, engine tests | reviewed | engine test suite and compile check passed | replaced duplicate M4-style math with the canonical M5.5 evaluator seam | yes |
| 7 | `01a0dd1b-87f1-7e73-8136-4ef0c1696e98` | persistence/restart review | `reviews/M6_PERSISTENCE_REVIEW.md` | reviewed | 13 store/API and cross-process checks passed | accepted restart, immutable-write, permissions, and bounded limitation evidence | yes |
| 8 | `01a0dd1b-d81f-7de3-965a-362521929b28` | persistence/restart review | same review file | reviewed | 8 checks reported, but scope duplicated row 7 | retained no additional contribution; not counted | no |
| 9 | `01a0dd1b-879e-7253-932e-518a55619e5d` | numerical pairing review | `reviews/M6_NUMERICAL_REVIEW.md` | reviewed | 23 focused tests passed | accepted same-sample, no-resampling, order, and no-op evidence; retained conditional findings | yes |
| 10 | `01a0dd1b-8851-7e40-bcb1-114076a12e0e` | frontend lifecycle/accessibility review | `reviews/M6_FRONTEND_REVIEW.md` | reviewed | TypeScript, 5 runtime tests, lint, and build passed | repaired stale-result and invalid-pair display findings; browser QA remains open | yes |
| 11 | `01a0dd1b-d7c1-72b0-a667-5a4ea4a0b489` | API safety/contract review | `reviews/M6_API_REVIEW.md` | reviewed | 16 focused API/contract/store tests passed | repaired disclaimer-bearing errors, typed projections, and persisted-result validation | yes |
| 12 | `01a0dd1b-873c-75e1-883f-01167445287c` | API safety/contract review | same review file | reviewed | 32 checks reported, but scope duplicated row 11 | retained no additional contribution; not counted | no |
| 13 | `01a0dd26-fa79-79e1-a30b-b37c452654a6` | provenance/lineage review | `reviews/M6_PROVENANCE_REVIEW.md` | reviewed | 11 focused provenance tests passed | accepted lineage and synthetic-label findings as bounded gates | yes |
| 14 | `01a0dd27-3807-7d80-9c7d-661dcb3ac077` | provenance/lineage review | same review file | reviewed | 16 checks reported, but scope duplicated row 13 | retained no additional contribution; not counted | no |
| 15 | `01a0dd27-38ce-7bd2-9541-ce23c4cfed0c` | security/safety review | `reviews/M6_SECURITY_REVIEW.md` | reviewed | route/error/storage/CORS/privacy review completed | accepted demo-only security boundary and disclaimer limitations | yes |
| 16 | `01a0dd27-3934-7d02-b457-a358d92aa96a` | scope/documentation review | `reviews/M6_SCOPE_REVIEW.md` | reviewed | current docs and implementation boundary audited | accepted stale-total and historical-verdict findings for documentation cleanup | yes |
| 17 | `01a0dd27-386c-7553-9683-b2902ae68ab5` | benchmark/reproducibility review | `reviews/M6_BENCHMARK_REVIEW.md` | reviewed | 21 focused tests and 50–1000 benchmark rerun passed | accepted deterministic/no-resampling evidence; retained full persisted-restart gap | yes |
| 18 | `01a0dd26-cef6-75d2-873b-0db9a807735c` | effect-statistics/invalid-pair review | `reviews/M6_STATS_REVIEW.md` | reviewed | 40 focused tests passed | tightened pair units, empty summaries, and result-status coupling; retained partial-delta limitation | yes |

The ledger currently records **36 counted substantive contributions**, including
the distinct review artifacts in the current campaign wave; the required
minimum of 20 is met. Overlapping persistence/API/provenance dispatches are
explicitly retained as not counted.

The lead will append one row for every actual dispatch. A contribution counts
only after review confirms it is useful, relevant, technically substantive,
and integrated or intentionally rejected with a documented reason.

## Gate checklist

- [x] Pre-flight blockers audited and repaired or explicitly bounded.
- [x] Paired contracts and stable pair identity are implemented.
- [x] The same baseline latent parameters are used for each counterfactual.
- [x] Scenario application reuses the canonical Python M5.5 deterministic seam.
- [x] Invalid pairs are retained, counted, and explained.
- [x] Effect metrics have explicit units and descriptive category thresholds.
- [x] Trial definitions/results persist across restart.
- [x] APIs expose creation, retrieval, effects, and pair inspection.
- [x] Frontend shows the paired experiment without implementing competing math.
- [x] Golden vectors, no-op, identity, order, immutability, and reproducibility tests pass.
- [x] M6 demo fixture is synthetic and visibly labeled.
- [x] Backend, frontend, runtime, lint, and build regressions pass.
- [x] Browser/accessibility status is honestly recorded as unavailable in this environment.
- [x] Credibility docs and root progress/decisions are updated.
- [x] M7 and M8 remain out of scope.
