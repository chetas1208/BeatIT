# M9 Evidence Review

Status: **review recorded — backend pass, frontend integration open**  
Date: 2026-09-26  
Scope: M8 Missing Piece contracts and routes, provenance/uncertainty language,
and `PlausibleTwinsPanel` integration into the M9 `EVIDENCE` space. This is a
read-only review; no production files were changed.

## Executive result

M8's deterministic Missing Piece implementation is reachable and bounded: the
API supports baseline-output and persisted Shadow Trial-effect analysis, checks
the ensemble/trial relationship, persists the result, and retains the
uncertainty-impact/Evidence Priority Score boundary. `PlausibleTwinsPanel` is
also mounted in the `/evidence` product branch.

The Evidence surface is not yet an end-to-end implementation of the M9
contract. It duplicates the experiment-owned ensemble workflow, does not mount
the existing component source-provenance list, cannot request Shadow Trial
effect analysis, and does not bind the returned analysis to the product
context. These are integration findings, not reasons to change the M8
deterministic engine in this review.

## Evidence inspected

- M8 scope and completion: `docs/hackathon/M8_AGENT_PLAN.md`,
  `docs/hackathon/M8_COMPLETION.md`, `docs/hackathon/M8_INFORMATION_GAIN_BOUNDARY.md`.
- M8 API and DTOs: `python/hearttwin/api.py:217-291`,
  `python/hearttwin/missing_piece/api_models.py:69-118`.
- M8 frontend: `web/components/twin/missing-piece/MissingPiecePanel.tsx:44-186`,
  `web/components/twin/ensemble/PlausibleTwinsPanel.tsx:65-128`.
- M9 ownership and journey requirements:
  `docs/hackathon/M9_INFORMATION_ARCHITECTURE.md` (surface ownership,
  EVIDENCE requirements, mandatory journey) and
  `docs/hackathon/M9_PRODUCT_STATE.md` (analysis identity and invalidation).
- M9 mounting: `web/components/layout/AppShell.tsx:116-132` and
  `web/components/twin/scenario/ScenarioPanel.tsx:45-54`.
- Existing source provenance component:
  `web/components/heart/evidence/EvidenceList.tsx:1-46`.

## Findings

| ID | Area | Result | Concrete finding |
|---|---|---|---|
| P1 | M8 Missing Piece API | **PASS** | `api.py:226-242` selects baseline or Shadow Trial-effect execution. For effects it requires a trial, loads the persisted trial, verifies `baseline_ensemble_id`, requires its immutable scenario definition, then calls `run_missing_piece_shadow_effect`. The result is persisted at `api.py:248`; retrieval is exposed at `api.py:254-291`. |
| P2 | Request boundary | **PASS** | `api_models.py:69-102` uses strict, extra-forbidden DTOs; restricts `target_kind` to `baseline_output`/`shadow_effect`; requires `shadow_trial_id` for effects and forbids it for baseline analysis; and sanitizes identifiers/evidence types. |
| P3 | Uncertainty/provenance language | **PASS** | The panel explicitly calls the output a deterministic local-sensitivity view and an “uncertainty-impact heuristic, not a probability or information-gain estimate” (`MissingPiecePanel.tsx:84-89`). It also labels simulated uncertainty separately (`PlausibleTwinsPanel.tsx:71-73,121`) and displays origin/seed/acceptance plus assumptions and warnings (`:102,117-121`). M8's information-gain boundary is consistent with this wording. |
| P4 | Basic EVIDENCE reachability | **PASS** | The M9 evidence branch mounts `PlausibleTwinsPanel` under an Evidence error boundary (`AppShell.tsx:129-130`), and the panel includes `MissingPiecePanel` when an ensemble exists (`PlausibleTwinsPanel.tsx:113-116`). The five-space navigation includes EVIDENCE in the prescribed order (`M9_INFORMATION_ARCHITECTURE.md`, navigation contract). |
| O1 | EVIDENCE ownership boundary | **OPEN** | `PlausibleTwinsPanel` exposes `Generate twins` in Evidence (`PlausibleTwinsPanel.tsx:77-85`) and the same full panel is still rendered by `ScenarioPanel` in Experiment (`ScenarioPanel.tsx:45-54`). M9 assigns ensemble generation to EXPERIMENT and Evidence analysis to EVIDENCE. Evidence should consume a matching persisted ensemble and provide a recovery link/state when it is absent, not create a competing ensemble workflow. |
| O2 | Source provenance integration | **OPEN** | The Evidence branch renders only the heart viewport plus `PlausibleTwinsPanel` (`AppShell.tsx:129-130`). The existing `EvidenceList` is defined but has no call site (`rg` finds only its definition), so source-map/component evidence is not shown in EVIDENCE. The panel shows ensemble lineage fields and assumptions, but not the source/artifact provenance and coverage that M9 requires first in the Evidence hierarchy. |
| O3 | Shadow Trial-effect Evidence path | **OPEN** | The backend supports `target_kind="shadow_effect"` and validates the trial, but `MissingPiecePanel.analyze()` sends only `baseline_ensemble_id` and `target_metric` (`MissingPiecePanel.tsx:44-50`). It has no `target_kind`, `shadow_trial_id`, or selected trial input. Therefore the M9 journey cannot reach the M8 effect-specific analysis from Evidence even when a valid Shadow Trial exists. |
| O4 | Analysis identity and freshness | **OPEN** | `MissingPiecePanel` keeps the response only in local component state (`MissingPiecePanel.tsx:37-41`) and does not expose the persisted analysis ID to the product context. `AppShell` constructs `analysisId: null` in the default context (`web/lib/product/contracts.ts:33-44`; the Evidence context is not populated). M9 requires Evidence to bind a matching persisted `analysisId` and distinguish stale results. |
| O5 | Cross-ensemble stale result risk | **OPEN** | Changing the selected/generated ensemble updates the `ensembleId` prop passed to `MissingPiecePanel` (`PlausibleTwinsPanel.tsx:114-116`), but the panel has no effect that clears or reloads its local `result` when `ensembleId` changes. A prior analysis can consequently remain visible beneath a newly selected ensemble, making its provenance appear current when it is not. |
| O6 | Provenance completeness in the visible Evidence surface | **OPEN** | The panel prints only a compact origin ID, seed, acceptance count, assumptions, and warnings (`PlausibleTwinsPanel.tsx:102,117-121`). The typed ensemble provenance also contains origin provenance, evidence IDs, physiology/distribution/prior versions, and creation time (`web/lib/twin/ensemble/contracts.ts:57-70`), but those fields are not surfaced or linked from Evidence. This is an auditability gap even though the backend payload retains them. |

## Disposition

The M8 numerical/contract boundary is accepted for this review, subject to the
existing M8 tests and documented limitations. The M9 Evidence integration is
**not closed** until O1–O6 are addressed or explicitly deferred with an honest
product-state decision. The highest-risk items are O1 (Evidence can create an
experiment artifact), O3 (no effect-analysis path), and O5 (possible stale
analysis presentation).

No browser, assistive-technology, or live backend verification is claimed here.
The M8 completion record already identifies those environment-limited gates;
this document records static integration evidence only.
