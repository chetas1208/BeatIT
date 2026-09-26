# Context & State Audit (Certification Wave A3)

Canonical model: `ConversationContext` in `python/hearttwin/assistant/schemas.py`.

## Field ownership (schema)

| Field | Intended source | Wired today? |
|-------|-----------------|--------------|
| `conversation_id` | Session | Panel generates UUID; not persisted server-side |
| `audience` | Mode (`general` / `physician`) | Panel sends `general` only |
| `patient_id` | Active case | Panel sends `caseId` from Zustand (Wave A fix) |
| `snapshot_id` | Timeline scrub | **Not sent** from UI |
| `component_id` | Heart click | **Not sent** — `contextEvents.ts` exists, no callers |
| `product_space` | M9 navigation | **Not sent** |
| `scenario_id`, `ensemble_id`, `shadow_trial_id`, `pair_id`, `target_metric` | Product features | **Not sent** |

## Companion model

`CaseContext` (`case_context.py`) adds `case_id`, lifecycle revision, historical
reference resolution — **not imported by `orchestrator.py`**.

## Stale-state / leak risks

1. **Cross-case:** New `conversationId` per panel mount but same browser session
   could reuse conversation id if panel stays open while `caseId` changes — panel
   does not reset turns or conversation id on case switch (**P1**).
2. **Cross-profile:** No server-side conversation store; risk is mainly wrong
   `patient_id` in context if user switches case without new conversation.
3. **Frontend/backend drift:** Backend `context_resolver` supports five event
   types; frontend never emits them into API requests.
4. **`case_id` vs `patient_id`:** Orchestrator now maps `patient_id` → `case_id`
   for tool dispatch only (documented alias; not a second context system).

## Recommendations (Wave C+)

- Merge `AssistantContext` store + `caseId` + product navigation into every
  `sendAssistantMessage` call.
- Reset conversation or inject case-change system event when `caseId` changes.
- Wire `resolve_case_context` into orchestrator pre-tool dispatch.
