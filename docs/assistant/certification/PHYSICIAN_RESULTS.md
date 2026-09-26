# Physician Support Results (Certification Wave C)

## Automated

- `test_certification_physician_scenarios.py` — treatment blocked (`HUMAN_DECISION_REQUIRED`), provenance-style questions safe.
- `test_physician_brief.py` — no `recommended_treatment` field; output safety scan.
- `test_language_integrity.py` — imperative treatment patterns flagged.

## UI

- BeatIT Copilot **Physician / General** toggle (`BeatITCopilotPanel.tsx`).
- Same API, same orchestrator; `audience` in `ConversationContext`.

## Gaps

- Physician brief artifact not auto-routed from chat intents.
- Legacy CopilotKit Q&A still OpenAI-backed when unified flag off.
- Full browser script (Wave E) not automated in CI.

## High-stakes

Treatment/diagnosis/emergency: pre-Laya input rail blocks autonomous clinical authority.
