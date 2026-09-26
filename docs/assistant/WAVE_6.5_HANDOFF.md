# Wave 6.5 Handoff — Physician Helper Hardening

> Runs after Wave 6 (`f5578b4`) and before Wave 7 (E2E + Chaos). Spec:
> `docs/assistant/PHYSICIAN_HELPER_HARDENING.md`.

## Status: integrated (backend + audit docs)

Python suite at integration: **1305+ passed** (see Wave 7 mount commit for
1309 after `/api/v1/assistant/message` landed).

## Deliverables

| Agent role | Artifact | Code |
|------------|----------|------|
| Case Context Hardening | `docs/architecture/CASE_CONTEXT_MODEL.md` | `python/hearttwin/assistant/case_context.py`, `tests/test_case_context.py` |
| Report Personalization | (design in module docstrings) | `report_personalization.py`, `tests/test_report_personalization.py` |
| Report Consistency | `docs/assistant/wave6.5/report-consistency.md` | `report_consistency.py`, `tests/test_report_consistency.py` |
| UI Cleanliness | `docs/ui/PHYSICIAN_HELPER_UI.md` | Safe fixes in assistant + legacy chat components (see audit) |
| Case isolation / report matrix | Covered by personalization + consistency tests | §60-style synthetic cases in `test_report_personalization.py` |

## What changed (product terms)

- **Case context** is an additive companion to Wave 2 `ConversationContext`
  (`case_id`, revision, historical-vs-current selection) without forking a
  second chat context system.
- **Reports** gain content-hierarchy logic so materially different synthetic
  cases produce materially different briefs, not swapped numbers on the same
  template.
- **Report consistency** extends numeric safety with unit, negation, uncertainty,
  and observed/derived boundary checks plus number-before-label coverage.
- **UI audit** documents leakage risks; Wave 4 assistant components and both
  legacy chat surfaces were reviewed. Shadow Trial / Split Heart / Missing
  Piece UI deferred until Codex-owned surfaces stabilize.

## Open items (carried to Wave 7+)

- `case_context.py` is **not yet wired** into `orchestrator.py` — tools that
  require `case_id` still need explicit context or a future dispatch bridge
  (BACKLOG item 8 partially addressed at the model layer only).
- Spec §102 architecture docs under `docs/architecture/` partially filed
  (`CASE_CONTEXT_MODEL.md` only); `PHYSICIAN_HELPER_CONTEXT.md`,
  `REPORT_PERSONALIZATION.md`, and testing matrices under `docs/testing/`
  remain optional follow-ups.
- Legacy dual chat (`CopilotDock`, `CareGuardCopilot`) still live; unified
  panel remains flag-gated (`NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED`).

## Security / medical

- No new autonomous clinical authority. Report and chat rails still use
  `safety_validator` + `language_integrity`.
- Cross-case contamination target **0** — enforced by tests on context keys and
  report personalization fixtures; full multi-tab UI chaos is Wave 7.

## Next wave

Wave 7: mount verification (done at start of Wave 7), multi-turn E2E
conversations, failure injection (Laya / models / keys), security audit,
final deliverables per campaign brief.
