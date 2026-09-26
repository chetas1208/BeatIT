# Wave 7 — E2E conversation scenarios (backend layer)

Automated coverage: `python/hearttwin/tests/test_assistant_e2e_conversations.py`.

| Campaign conv | Backend test | Notes |
|---------------|--------------|-------|
| A — component → patient → provenance | `test_conversation_a_component_context_without_restatement` | Same `conversation_id` + `component_id=LV`; full generative answers deferred while Laya intent policy defers to clarification |
| B — longitudinal / experiment / uncertainty | *pending* | Needs `ensemble_id` / scenario fixtures in multi-turn script |
| C — no treatment recommendation | `test_conversation_c_refuses_autonomous_treatment_plan` | `HUMAN_DECISION_REQUIRED`, zero tools |
| D — observed vs simulated | `test_conversation_d_observed_vs_simulated_is_not_fabricated` | Asserts no tool fabrication; may clarify until evidence tools wired with `case_id` |

Live app route: `POST /api/v1/assistant/message` — `test_assistant_api_mount.py`.

Frontend one-panel E2E (flag on, artifact cards, context events) remains manual
or a future Playwright pass.
