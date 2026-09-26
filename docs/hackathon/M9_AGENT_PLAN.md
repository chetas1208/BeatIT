# M9 Agent Plan — Unified Product Experience

Last updated: 2026-09-26

## Scope and gate

M9 consolidates the existing cardiac twin, experiment, comparison, evidence,
and report capabilities into one product journey. The five primary spaces are
`TWIN`, `EXPERIMENT`, `COMPARE`, `EVIDENCE`, and `REPORT`. Numerical physiology,
ensemble generation, Shadow Trial pairing, and Missing Piece calculations are
read-only authorities for this milestone. M10 and M10.5 are out of scope.

The lead owns shared shell integration (`web/components/layout/AppShell.tsx`),
the final route/state wiring, and all conflict resolution. Agents must keep
their edits inside the paths listed below and return verification evidence.

| ID | Responsibility | Owned paths | Deliverable | Status | Review |
|---|---|---|---|---|---|
| 01 | M8/M7/M6 gate preflight | `docs/hackathon/M9_PREFLIGHT.md` | inherited gate audit | complete | reviewed: conditional implementation go; browser/reload/inherited gates remain open |
| 02 | information architecture | `docs/hackathon/M9_INFORMATION_ARCHITECTURE.md` | five-space map | complete | reviewed: exactly five spaces and mandatory journey |
| 03 | product state contract | `docs/hackathon/M9_PRODUCT_STATE.md` | context/state rules | complete | reviewed: lineage, invalidation, privacy, and reload rules |
| 04 | interaction contract | `docs/hackathon/M9_INTERACTIONS.md` | drawer and flow rules | complete | reviewed: Escape, outside click, focus, and honest async states |
| 05 | design system audit | `docs/hackathon/M9_DESIGN_SYSTEM.md` | token/component rules | complete | reviewed: existing token foundation and visual exceptions recorded |
| 06 | human-factors review | `docs/hackathon/M9_HUMAN_FACTORS.md` | cognitive-load review | complete | reviewed: 20 actionable acceptance checks |
| 07 | accessibility review | `docs/hackathon/M9_ACCESSIBILITY.md` | keyboard/semantics audit | complete | reviewed: source-level keyboard/AT audit; browser gate open |
| 08 | performance review | `docs/hackathon/M9_PERFORMANCE.md` | render/bundle budget | complete | reviewed: source hotspots and proposed budgets; no invented measurements |
| 09 | test-matrix author | `docs/hackathon/M9_TEST_MATRIX.md` | required matrix | planned | |
| 10 | Twin surface audit | `docs/hackathon/reviews/M9_TWIN_REVIEW.md` | heart/timeline/source audit | planned | not delivered; browser/source inspection remains open |
| 11 | Experiment surface audit | `docs/hackathon/reviews/M9_EXPERIMENT_REVIEW.md` | causal/Shadow Trial audit | complete | reviewed: bounded flow and stale-result risks recorded |
| 12 | Compare surface audit | `docs/hackathon/reviews/M9_COMPARE_REVIEW.md` | Split Heart audit | complete | reviewed: 28 focused comparison tests; conditional pass |
| 13 | Evidence surface audit | `docs/hackathon/reviews/M9_EVIDENCE_REVIEW.md` | provenance/Missing Piece audit | complete | reviewed: M8 boundaries pass; integration/open findings recorded |
| 14 | Report surface audit | `docs/hackathon/reviews/M9_REPORT_REVIEW.md` | report contract audit | complete | reviewed: pure/safety-aware; lineage/stale gates open |
| 15 | provenance interaction review | `docs/hackathon/reviews/M9_PROVENANCE_REVIEW.md` | click-to-inspect boundary | complete | reviewed: passive badge and keyboard disclosure gaps recorded |
| 16 | synthetic-data reviewer | `docs/hackathon/reviews/M9_SYNTHETIC_DATA_REVIEW.md` | observed/derived/synthetic language | complete | reviewed: labels and demo-only boundary |
| 17 | medical/data integrity reviewer | `docs/hackathon/reviews/M9_MEDICAL_DATA_REVIEW.md` | safety and lineage review | complete | reviewed: no-go for patient data; demo-only conditional |
| 18 | visual/product reviewer | `docs/hackathon/reviews/M9_VISUAL_PRODUCT_REVIEW.md` | hierarchy/continuity review | complete | reviewed: hierarchy passes; browser/token/continuity gaps open |
| 19 | accessibility adversarial reviewer | `docs/hackathon/reviews/M9_ACCESSIBILITY_REVIEW.md` | failure-mode review | complete | reviewed: focus/AT/WebGL risks and blockers |
| 20 | performance adversarial reviewer | `docs/hackathon/reviews/M9_PERFORMANCE_REVIEW.md` | failure-mode review | planned | |
| 21 | security reviewer | `docs/hackathon/reviews/M9_SECURITY_REVIEW.md` | URL/data exposure review | complete | reviewed: mode-only URL passes; patient-data/CORS gates remain open |
| 22 | architecture reviewer | `docs/hackathon/reviews/M9_ARCHITECTURE_REVIEW.md` | seam/ownership review | complete | reviewed: shell ownership and authority boundaries |
| 23 | loading/error/empty reviewer | `docs/hackathon/reviews/M9_STATE_REVIEW.md` | non-fake states | complete | reviewed: state surface gaps recorded |
| 24 | responsive reviewer | `docs/hackathon/reviews/M9_RESPONSIVE_REVIEW.md` | narrow/wide behavior | complete | reviewed: conditional pass; nested scroll and WebGL risks |
| 25 | navigation model engineer | `web/lib/product/navigation.ts` | mode/path mapping | lead-integrated | TypeScript, runtime test, route smoke passed |
| 26 | product contract engineer | `web/lib/product/contracts.ts` | typed five-space contract | lead-integrated | typed context and five-space constants integrated |
| 27 | report contract engineer | `web/lib/product/reportContracts.ts` | deterministic report DTO | lead-integrated | 2 report contract tests passed |
| 28 | source status model engineer | `web/lib/product/sourceStatus.ts` | provenance/status labels | lead-integrated | status labels integrated in shell/report |
| 29 | deep-link test engineer | `web/lib/product/__tests__/navigation.test.ts` | path mapping tests | lead-integrated | route mapping test passed |
| 30 | report model test engineer | `web/lib/product/__tests__/reportContracts.test.ts` | report contract tests | lead-integrated | report readiness/unavailable tests passed |
| 31 | visual regression reviewer | `docs/hackathon/reviews/M9_VISUAL_REGRESSION.md` | existing style regression | planned | |
| 32 | integration test reviewer | `docs/hackathon/reviews/M9_INTEGRATION_REVIEW.md` | journey seam review | planned | |
| 33 | browser QA recorder | `docs/hackathon/M9_QA.md` | manual/browser evidence | planned | |
| 34 | completion auditor | `docs/hackathon/M9_COMPLETION.md` | final gate audit | planned | |
| 35 | decision recorder | `docs/hackathon/M9_DECISIONS.md` | accepted tradeoffs | planned | |
| 36 | documentation consistency reviewer | `docs/hackathon/reviews/M9_DOCS_REVIEW.md` | docs consistency | planned | |
| 37 | frontend dependency reviewer | `docs/hackathon/reviews/M9_FRONTEND_DEPENDENCY_REVIEW.md` | dependency boundary | planned | |
| 38 | observability reviewer | `docs/hackathon/reviews/M9_OBSERVABILITY_REVIEW.md` | user-facing telemetry boundary | planned | |
| 39 | return-path reviewer | `docs/hackathon/reviews/M9_RETURN_PATH_REVIEW.md` | return Twin continuity | planned | |
| 40 | release reviewer | `docs/hackathon/reviews/M9_RELEASE_REVIEW.md` | M9/M10 boundary | planned | |

## Counting rule

An entry counts only after the lead has inspected the changed path and the
agent has supplied substantive findings or a tested implementation. Duplicate,
placeholder, and unverified work does not count. The ledger is updated only
after review; dispatch alone is never completion evidence.

## Review tally

21 substantive agent contributions are complete and reviewed in this ledger.
The Twin surface review remains planned because no separate Twin-only artifact
was delivered; this does not reduce the completed contribution count below the
required 20. Lead-integrated contract/test rows are listed separately and are
not included in the 21-agent tally.
