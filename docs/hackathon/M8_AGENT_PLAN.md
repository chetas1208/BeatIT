# M8 Agent Plan — Missing Piece

Last updated: 2026-09-26

## Scope and gate

M8 adds deterministic sensitivity analysis, uncertainty-impact attribution,
evidence-to-parameter mapping, target-dependent evidence ranking, and a bounded
Missing Piece surface. The deterministic cardiac engine, M5 parameter
distributions, M6 paired Shadow Trial, and M7 comparison remain authorities.
M9/M10/M10.5 are out of scope.

At least 20 contributions below must complete, be reviewed by the lead, and be
meaningful. Dispatching or naming work does not count. Shared central files are
lead-owned unless explicitly assigned.

| ID | Responsibility | Owned paths | Dependencies | Deliverable | Status | Review | Integration |
|---|---|---|---|---|---|---|---|
| 01 | M7/M5/M6 preflight auditor | `docs/hackathon/M8_PREFLIGHT.md` | M5-M7 | prerequisite audit | complete | reviewed: M5.5 projection bases, M6 pairing, M7 comparison seam verified | accepted |
| 02 | Mathematical architecture auditor | `docs/hackathon/M8_MATH_AUDIT.md` | preflight | method boundary | complete | reviewed: Tier-1 finite-difference boundary documented | accepted |
| 03 | Sensitivity contract engineer | `python/hearttwin/missing_piece/contracts.py` | math audit | typed contracts | complete | reviewed: strict models, unsupported method rejection | accepted |
| 04 | Local sensitivity engine | `python/hearttwin/missing_piece/sensitivity.py` | contracts | finite perturbation method | complete | reviewed: canonical `_baseline`/`_evaluate`, bounded central/one-sided differences, compile/import passed | accepted; lead will add persisted-sample seam and normalized response fields if required |
| 05 | Perturbation policy engineer | `python/hearttwin/missing_piece/perturbations.py`, `python/hearttwin/tests/test_missing_piece_perturbations.py` | M5 bounds | bounded policies | complete | reviewed: native/fractional steps, range cap, boundary method, 12 focused tests passed | accepted |
| 06 | Sensitivity golden tests | `python/hearttwin/tests/test_missing_piece_sensitivity.py` | 04,05 | known-vector tests | complete | reviewed: deterministic derivative, bounds, target specificity, immutability, safety language; 5 tests passed | accepted |
| 07 | Global sensitivity engineer | `python/hearttwin/missing_piece/global_sensitivity.py`, `python/hearttwin/tests/test_missing_piece_global_sensitivity.py` | contracts | optional transparent method | complete | reviewed: median absolute local-response aggregate, explicit rejection of Sobol/Morris/Shapley labels; 2 tests passed | accepted as descriptive aggregate only |
| 08 | Identifiability engineer | `python/hearttwin/missing_piece/identifiability.py`, `python/hearttwin/tests/test_missing_piece_identifiability.py` | distributions | parameter identifiability | complete | reviewed: descriptive-only/unavailable/unsupported statuses; 2 tests passed | accepted; no uniqueness claim |
| 09 | Uncertainty magnitude engineer | `python/hearttwin/missing_piece/uncertainty_agent.py`, `python/hearttwin/tests/test_missing_piece_uncertainty_agent.py` | M5 distributions | uncertainty magnitude cross-check | complete | reviewed: accepted samples, q05/q95, bounds, explicit unavailable; 2 tests passed | accepted as independent audit implementation; lead engine uses reviewed `uncertainty.py` |
| 10 | Uncertainty impact engineer | `python/hearttwin/missing_piece/impact.py`, `python/hearttwin/tests/test_missing_piece_impact.py` | 04,09 | labeled impact heuristic | complete | reviewed: normalized response preference, invalid-value filtering, deterministic sort, 3 tests passed | accepted |
| 11 | Shadow Trial driver engineer | `python/hearttwin/missing_piece/effect_drivers.py` | M6 | paired effect drivers | complete | reviewed: same-sample fixed-target effect sensitivity implemented and golden-locked | accepted |
| 12 | Effect-driver tests | `python/hearttwin/tests/test_missing_piece_effect_drivers.py` | 11 | driver fixtures | complete | reviewed: M6 seam, same-sample/fixed-target/missing-base/safety tests; 5 tests passed | accepted as contract tests; production driver remains open |
| 13 | Evidence taxonomy engineer | `python/hearttwin/missing_piece/evidence.py`, `python/hearttwin/tests/test_missing_piece_evidence.py` | existing provenance | evidence classes | complete | reviewed: versioned immutable taxonomy, deterministic ordering, educational proxy boundary; 3 focused tests passed | accepted |
| 14 | Evidence-to-parameter mapper | `python/hearttwin/missing_piece/evidence_map.py`, `python/hearttwin/tests/test_missing_piece_evidence_map.py` | 13 | explicit rationale map | complete | reviewed: allowlisted mappings, strength weights, target filtering, unsupported/duplicate rejection; 5 tests passed | accepted |
| 15 | Evidence freshness engineer | `python/hearttwin/missing_piece/freshness.py`, `python/hearttwin/tests/test_missing_piece_freshness.py` | 13 | freshness scoring | complete | reviewed: deterministic reference time/half-life, unavailable handling, no clinical-validity claim; 4 tests passed | accepted |
| 16 | Completeness engine engineer | `python/hearttwin/missing_piece/completeness.py`, `python/hearttwin/tests/test_missing_piece_completeness.py` | 13 | domain completeness | complete | reviewed: declared coverage, uncovered parameters, explicit limitations; 3 tests passed | accepted |
| 17 | Evidence-value heuristic engineer | `python/hearttwin/missing_piece/evidence_value.py`, `python/hearttwin/tests/test_missing_piece_evidence_value.py` | 14,16 | target-specific heuristic | complete | reviewed: weighted impact score, target filtering, duplicate rejection; 3 tests passed | accepted |
| 18 | Information-gain boundary auditor | `docs/hackathon/M8_INFORMATION_GAIN_BOUNDARY.md` | 17 | no-fake-IG boundary | complete | reviewed: rejects entropy/posterior/EVI/mutual-information/clinical claims and lists future prerequisites | accepted |
| 19 | Missing Piece orchestration engineer | `python/hearttwin/missing_piece/engine.py`, `python/hearttwin/tests/test_missing_piece_engine_review.py` | 04,10,14,16,17 | deterministic aggregate | complete | reviewed: persisted-base authority, target validation, unavailable handling, normalized response; 6 tests passed | accepted |
| 20 | Missing Piece API engineer | `python/hearttwin/missing_piece/api_models.py` | 19 | API DTOs | lead-integrated | worker shut down without a contribution; lead strict DTO tests pass | not counted as agent contribution |
| 21 | Missing Piece persistence engineer | `python/hearttwin/storage/missing_piece_store.py` | 20 | durable persistence | lead-integrated | worker shut down without a contribution; lead restart/immutability tests pass | not counted as agent contribution |
| 22 | API route integration engineer | `python/hearttwin/api.py` | 20,21 | bounded routes | lead-integrated | baseline and persisted Shadow Trial-effect Missing Piece routes added; API import and full suite pass | not counted as agent contribution |
| 23 | Frontend contract adapter | `web/types/missing-piece.ts`, `web/lib/api.ts` | 20 | typed wire adapter | complete | reviewed: snake_case alignment, encoded IDs, API object exposure; TypeScript and ESLint passed | accepted |
| 24 | Missing Piece UI engineer | `web/components/twin/missing-piece/MissingPiecePanel.tsx` | 23 | target-dependent UI | complete | reviewed: accessible loading/empty/error/success, target selector, WHY/WHAT language, safety disclaimer; TypeScript and ESLint passed | accepted |
| 25 | Sensitivity visualization engineer | `web/components/twin/missing-piece/SensitivityTable.tsx` | 23 | transparent table | complete | reviewed: caption/scopes, responsive overflow, unavailable handling, explicit local heuristic labels; ESLint passed and lead TypeScript passed | accepted |
| 26 | Evidence map UI engineer | `web/components/twin/missing-piece/EvidenceMap.tsx` | 23 | evidence rationale UI | lead-integrated | rationale, constrained parameters, priority labels, and empty state implemented; frontend gates pass | not counted as agent contribution |
| 27 | Split-heart uncertainty engineer | `web/components/twin/comparison/UncertaintyOverlay.tsx` | M7,23 | bounded overlay | lead-integrated | scalar-only overlay explicitly refuses geometric inference; TypeScript/lint/build pass | not counted as agent contribution |
| 28 | Component inspector integration | `web/lib/twin/comparison/m8Inspector.ts` | M7,23 | uncertainty handoff | lead-integrated | target/impact/evidence/limitation adapter implemented; TypeScript/lint pass | not counted as agent contribution |
| 29 | Frontend runtime tests | `web/lib/twin/missing-piece/__tests__/inspectorModel.test.ts` | 23-28 | UI model tests | complete | reviewed: m8Inspector mapping + disclaimer boundary; vitest 2 passed | accepted |
| 30 | Performance engineer | `docs/hackathon/M8_PERFORMANCE.md` | engine | benchmark | complete | reviewed: scaling/benchmark command/scalar overlay boundary documented without invented measurements | accepted |
| 31 | Mathematical integrity reviewer | `docs/hackathon/reviews/M8_MATH_REVIEW.md` | freeze | adversarial review | complete | reviewed: pass/fail findings on units, bounds, normalization, unavailable handling, heuristic terminology, unsupported global claims, and Shadow Trial gaps; 60 focused M8 tests passed | accepted |
| 32 | Cardiac physiology reviewer | `docs/hackathon/reviews/M8_CARDIAC_REVIEW.md` | freeze | unsupported-claim review | complete | reviewed: conditional pass on proxy mappings/perturbations | accepted |
| 33 | Experimental-design reviewer | `docs/hackathon/reviews/M8_EXPERIMENTAL_DESIGN.md` | freeze | ranking review | complete | reviewed: conditional pass; documented taxonomy/global-map limits | accepted |
| 34 | UX/language reviewer | `docs/hackathon/reviews/M8_UX_LANGUAGE.md` | freeze | safety-language review | complete | reviewed: pass on simulation framing and table a11y | accepted |
| 35 | Browser/accessibility reviewer | `docs/hackathon/reviews/M8_BROWSER_ACCESSIBILITY.md` | freeze | manual QA | complete | reviewed: environment-blocked; static a11y pass documented | accepted as blocked gate |
| 36 | M9-boundary reviewer | `docs/hackathon/reviews/M8_M9_BOUNDARY.md` | freeze | scope review | complete | reviewed: pass; reusable APIs without M9 shell | accepted |
| 37 | Golden fixture engineer | `fixtures/golden/missing_piece/`, `python/hearttwin/tests/test_missing_piece_golden_fixtures.py` | 19 | reproducibility vectors | complete | reviewed: 9 cases incl. shadow-trial-driver; pytest passed | accepted |
| 38 | Sensitivity cache engineer | `python/hearttwin/missing_piece/sensitivity_cache.py`, tests | 04 | config-keyed cache | complete | reviewed: process-local invalidation on engine version; 2 tests passed | accepted |
| 39 | API subresource engineer | `python/hearttwin/api.py`, `test_missing_piece_api_routes.py` | 21 | drivers + evidence-ranking GET | complete | reviewed: slices persisted payload + disclaimer; route test passed | accepted |
| 40 | M8 documentation pack | `docs/hackathon/M8_ARCHITECTURE.md` … `M8_DECISIONS.md` | freeze | architecture/sensitivity/evidence docs | complete | reviewed: semantics match implementation | accepted |
| 41 | Architecture reproducibility reviewer | `docs/hackathon/reviews/M8_ARCHITECTURE_REPRODUCIBILITY.md` | freeze | reproducibility review | complete | reviewed: conditional pass | accepted |

## Counting rule

The lead will record completion only after inspecting changed paths and
verification evidence. Failed, duplicate, or documentation-only placeholder
work does not count unless it produces a substantive audit decision.
