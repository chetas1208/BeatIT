# E2E Results (Certification Wave E)

## Backend (automated)

| Script | File | Status |
|--------|------|--------|
| Conversations A,C,D | `test_assistant_e2e_conversations.py` | PASS |
| API mount | `test_assistant_api_mount.py` | PASS |
| Physician C1 | `test_certification_physician_scenarios.py` | PASS |
| Isolation | `test_certification_patient_isolation.py` | PASS |
| Failure matrix | `test_certification_failure_matrix.py` | PASS |

## Browser (manual / Wave E1)

Full product script (Twin → chat → timeline → experiment → Shadow Trial → Compare → Evidence → Report) requires:

- `NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED=true`
- Backend on `:8000`, web on `:3000`

**Not automated in repo** (no Playwright suite). Mark **PARTIAL** until browser agent run recorded.

## Required conversation B (multi-tool)

Not fully automated — needs scenario/ensemble/shadow IDs in context from UI; context wiring added in certification integration (component, snapshot, case, ensemble, pair fields).
