# Request Path Trace (Certification Wave A2)

One unified-assistant message (`POST /api/v1/assistant/message`), happy path
and fallback path. File:function citations are the integration truth as of
Wave A.

## Browser → frontend

1. User opens **BeatIT Copilot** (`BeatITCopilotTrigger.tsx`) when
   `NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED=true`.
2. User submits text → `BeatITCopilotPanel.tsx::handleSubmit`.
3. `web/lib/assistantApi.ts::sendAssistantMessage` →
   `fetch(\`${NEXT_PUBLIC_API_BASE}/assistant/message\`)` (base is
   `/api/v1`, so full path `/api/v1/assistant/message`).
4. JSON body: `AssistantRequest` — `conversation_id`, `message`,
   `context` (`conversation_id`, `audience`, optional `patient_id` from
   `useDualBeatStore.caseId`).

**Gap:** `contextEvents.ts` / product-space fields are not merged into this
request yet.

## Backend entry

5. `python/hearttwin/api.py` — `app.include_router(_assistant_router, prefix="/api/v1/assistant")`.
6. `assistant/router.py::post_message` — Pydantic validates `AssistantRequest`.
7. `assistant/orchestrator.py::handle_message`.

## Request control plane (orchestrator)

8. **Input rail:** `safety_validator.classify_request_safety` — blocks
   emergency/diagnosis/treatment → `HUMAN_DECISION_REQUIRED`.
9. **Context resolution:** `context_resolver.resolve_context` — bare
   referents / ambiguity → `CLARIFICATION_REQUIRED`.
10. **System-1:** `LayaAdapter.classify_intent`, `select_tool_family`
    (HTTP to Laya when configured, else deterministic fallback in
    `laya_adapter.py`).
11. **Execution policy:** `_select_and_execute_tool` — matches tool required
    args to `ConversationContext` (`case_id` may alias from `patient_id`).
12. If tool runs: render deterministic text from `ToolResult.canonical_payload`;
    **output rail:** `check_output_safety`, `validate_numeric_claims`.
13. If no tool: **model router** `_generate_model_response` — consults
    `laya_policy.should_defer_to_clarification` (currently conservative) →
    optional `model_client.chat_completion` via `model_pool` → same output rails.

## Data plane (when tools run)

| Tool | Authority |
|------|-----------|
| `get_ensemble*` | `storage/ensemble_store.py` persisted ensemble |
| `get_cardiac_findings`, `get_pv_loop`, … | `tools/storage.get_case` → `CaseRecord` / `derive_findings` / simulation results |

## Response → frontend

14. `AssistantResponse` — `message`, `execution_class`, `artifacts[]`,
    `trace`, `safety_disclaimer`.
15. Panel appends turn; artifact chips are stubbed (`ArtifactCard` / detail
    panel partially implemented).

## Parallel legacy path (still live for most users)

- **CopilotDock** → `web/app/api/copilotkit/route.ts` → backend `/copilotkit`
  → `copilot.py` actions (deterministic pipeline + OpenAI Q&A).

Does not pass through `orchestrator.handle_message`.
