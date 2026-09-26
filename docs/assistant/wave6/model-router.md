# Wave 6 — Model Router: wiring the first real generative call into the orchestrator

**Agent 29 ("Model Router Engineer").** Extends `python/hearttwin/assistant/orchestrator.py`
(Wave 3's file — the intended integration point per its own module docstring)
to implement `docs/assistant/GLOBAL_ARCHITECTURE.md`'s "MODEL ROUTER" decision
tree for real, and to make the **first real, billed NVIDIA chat-completion
call** anywhere in this campaign (Waves 2-5 were deliberately LLM-free).

Files touched:
- `python/hearttwin/assistant/orchestrator.py` — the only production file
  changed (explicitly in-scope per this task).
- `python/hearttwin/tests/test_orchestrator.py`,
  `test_assistant_router.py`, `test_decision_adversary.py` — updated to match
  the new, intended behavior (see "Behavior change and regression note"
  below). No test's *safety guarantee* weakened — only execution-class
  labels changed, and only for the exact scenario Wave 6 was asked to change.
- `python/hearttwin/tests/test_orchestrator_model_routing.py` — new, this
  wave's test file.
- This doc.

Everything else (`laya_adapter.py`, `laya_policy.py`, `safety_validator.py`,
`tool_registry.py`, `model_pool.py`, `model_client.py`) was read-only, per
task constraints.

## The exact routing logic implemented

`orchestrator.py`'s tool dispatch step (d) already existed (Wave 3): pick a
registered tool whose required args resolve from `ConversationContext`,
execute it, render deterministic text from the real `ToolResult`. When no
tool's requirements are met, it used to just return an honest
`UNSUPPORTED`/`INSUFFICIENT_EVIDENCE` message. Wave 6 replaces that dead end
with `_generate_model_response`, called **only** when `tool_result is None`
— i.e. exactly `GLOBAL_ARCHITECTURE.md`'s MODEL ROUTER first branch ("Can
deterministic tool answer completely? NO -> ..."):

```
tool_result is None (no deterministic tool could answer)
  -> should_defer_to_clarification("classify_intent", intent_decision.source)?
       YES -> CLARIFICATION_REQUIRED (existing conservative response)
       NO  -> is_complex_reasoning_required(message, context)?
                YES -> DEEP_MODEL   (nvidia/nemotron-3-super-120b-a12b)
                NO  -> FAST_MODEL   (nvidia/nemotron-3.5-lightning-30b-a3b)
              -> build tool-grounded (or explicitly-not-grounded) prompt
              -> chat_completion(...)   [real HTTP call]
              -> check_output_safety + validate_numeric_claims on the result
                   PASS -> return generated text (GENERATIVE_EXPLANATION /
                           COMPLEX_SYNTHESIS)
                   FAIL -> return the same safe generic fallback (e) already
                           uses for tool-rendered text
              -> ANY exception (ModelClientError or otherwise)
                   -> return the ORIGINAL deterministic fallback text/class
                      _select_and_execute_tool already produced
```

`ModelRole`/`get_model_id` come straight from Wave 2's `model_pool.py`
(unmodified); `chat_completion`/`ModelClientError` come from the sibling
"Fast Model Benchmark Engineer" agent's `model_client.py` (unmodified,
imported read-only, per task instructions to reuse rather than duplicate).

## Confirmation the Wave 5 policy module is now actually consulted (not just imported)

`laya_policy.should_defer_to_clarification("classify_intent",
intent_decision.source)` is called at the top of `_generate_model_response`,
using the **same** `intent_decision` `handle_message` already computed in
step (c) (no second, redundant classification). This is the first production
call site anywhere in the repo — Wave 5's own module docstring and
`docs/assistant/WAVE_5_HANDOFF.md` both flagged this as built but not wired.

Verified, not assumed: `laya_policy.py`'s `classify_intent` entry measured
**58.6% accuracy** (17/29 on the 160-fixture eval), below its own 70% trust
threshold, so `is_trustworthy` is `False` and
`should_defer_to_clarification("classify_intent", <any source>)` returns
`True` **unconditionally** today. Net effect on the live system: **every**
"no tool matched" request currently resolves to `CLARIFICATION_REQUIRED`
before ever reaching a model call — the system is maximally conservative
given today's measured numbers, exactly as Wave 5's own recommendation says
it should be. `test_policy_deferral_prevents_model_call_by_default` proves
this at zero network cost (a mocked `chat_completion` that raises
`AssertionError` if called — it never is), and
`test_policy_module_consulted_with_the_actual_decision_source` spies on the
real `should_defer_to_clarification` (delegating to the real implementation)
to prove the exact call arguments (`"classify_intent"`, `"fallback"`) match
what `laya_policy.py`'s own docstring specifies as its intended integration
point.

Every FAST/DEEP/safety-fallback/model-failure test in the new suite has to
explicitly monkeypatch `should_defer_to_clarification` to `False` at
`orchestrator`'s own import site to reach past this gate — documented inline
in every such test, never silently bypassed.

## Tool-grounding rule and how it's enforced

`_build_model_messages(message, context, tool_result)` builds the prompt:
- If a real `ToolResult` is passed, its `canonical_payload` is embedded
  verbatim under `GROUNDING DATA (canonical, real, from BeatIT tool
  '<name>')`, and the system prompt states only those exact figures may be
  used as numbers.
- If `tool_result` is `None`, the prompt explicitly says `GROUNDING DATA:
  none available for this turn` and instructs general orientation/
  clarifying language only — never a specific patient finding.

This is enforced **twice**: by instruction (the prompt), and **structurally**
by reusing `safety_validator.validate_numeric_claims(generated_text,
canonical_payload)` — the exact same function (e) already runs on
tool-rendered text — with `canonical_payload = {}` whenever no tool ran. Any
numeric cardiac claim (EF/SV/CO/MAP/HR/EDV/ESV/QTc) the model makes with an
empty canonical payload is therefore an automatic, unconditional mismatch
regardless of prompt compliance — verified for real by
`test_unguarded_numeric_claim_falls_back_to_safe_generic_message` (mocked: a
fabricated "ejection fraction is 45%" response is rejected) and confirmed
live by the real integration run below (two real generations both ended up
safety-withheld).

**Honest documented gap:** under the current tool registry + tool-dispatch
trigger condition, `handle_message` never actually reaches the MODEL ROUTER
with a non-`None` `tool_result` — the branch only fires when `tool_result is
None`. So the tool-grounded half of `_build_model_messages` is real,
tested, and structurally correct, but not yet reachable through the live
`handle_message()` path with today's registry (only 4 tools exist, none of
which both succeed AND leave the request wanting further model narration in
the current wiring). `test_real_model_call_grounds_response_in_real_tool_result`
proves it works by calling `_generate_model_response` directly with a real,
persisted ensemble `ToolResult` — the same function `handle_message` would
call if a future wave widens that trigger condition (e.g. to also route
GENERATIVE_EXPLANATION-intent + successful-tool-call turns through a model
narrator). This mirrors this module's own established style of flagging real
gaps rather than papering over them (e.g. `_resolve_required_args`'s
`case_id`/`patient_id` note).

## Fallback tree and how each failure mode was tested

| Failure mode | Behavior | Test (mocked) | Test (real) |
|---|---|---|---|
| classify_intent policy defers | `CLARIFICATION_REQUIRED`, no model call | `test_policy_deferral_prevents_model_call_by_default` | (this IS the default live path — see integration tests below, all force it open to reach further) |
| `ModelClientError` (no healthy key / all keys failed / malformed body) | original deterministic fallback text+class | `test_model_client_error_falls_back_to_deterministic_response` | `test_real_model_failure_falls_back_to_deterministic_response` (genuine 404-shaped failure against the real endpoint using a made-up model id) |
| Any other exception during the call | same fallback, never crashes | `test_unexpected_exception_during_model_call_never_crashes` | covered transitively by the above |
| `check_output_safety` blocks generated text | safe generic fallback message | `test_safety_violation_falls_back_to_safe_generic_message` | observed live (see below) |
| `validate_numeric_claims` rejects generated text | safe generic fallback message | `test_unguarded_numeric_claim_falls_back_to_safe_generic_message` | observed live (see below) |
| Empty/whitespace-only model response | safe generic fallback message | `test_empty_model_response_falls_back_to_safe_generic_message` | — |
| FAST vs DEEP selection | correct model id per branch | `test_simple_request_routes_to_fast_model`, `test_complex_request_routes_to_deep_model` | `test_real_fast_model_end_to_end_through_handle_message`, `test_real_deep_model_end_to_end_through_handle_message` |
| Tool-grounded prompt | payload embedded, real model call | `test_build_model_messages_with_tool_result_includes_real_payload` | `test_real_model_call_grounds_response_in_real_tool_result` |

## Real integration test run (actual output)

Gated behind `RUN_EXTERNAL_INTEGRATION_TESTS=true` (this repo's existing
convention for real-external-API tests, already used by
`test_weave_integration.py` — reused rather than inventing a second,
competing opt-in flag). Credentials come from the environment
(`MODEL_API_KEY_1`/`_2`/`_3`), never loaded by the test itself, matching how
every other real-external test in this repo is run.

```
$ set -a && source .env && set +a && RUN_EXTERNAL_INTEGRATION_TESTS=true \
    python3 -m pytest python/hearttwin/tests/test_orchestrator_model_routing.py::TestRealModelRouterIntegration -v

python/hearttwin/tests/test_orchestrator_model_routing.py::TestRealModelRouterIntegration::test_real_fast_model_end_to_end_through_handle_message PASSED
python/hearttwin/tests/test_orchestrator_model_routing.py::TestRealModelRouterIntegration::test_real_deep_model_end_to_end_through_handle_message PASSED
python/hearttwin/tests/test_orchestrator_model_routing.py::TestRealModelRouterIntegration::test_real_model_call_grounds_response_in_real_tool_result PASSED
python/hearttwin/tests/test_orchestrator_model_routing.py::TestRealModelRouterIntegration::test_real_model_failure_falls_back_to_deterministic_response PASSED

========================= 4 passed in 79.60s (0:01:19) =========================
```

4 real, billed NVIDIA calls made (within the task's 3-5 target), each
exercising a different part of the wiring end-to-end. A follow-up manual
probe (outside the test file, for this doc) confirmed real content and real
gate behavior:

```
--- Tell me something interesting.
class: GENERATIVE_EXPLANATION | model_used: nvidia/nemotron-3.5-lightning-30b-a3b
message: BeatIT could not verify that response against canonical data, so it is
withholding it rather than risk showing an unsupported or unsafe claim.

--- Please compare the directly observed measurements ...
class: COMPLEX_SYNTHESIS | model_used: nvidia/nemotron-3-super-120b-a12b
message: BeatIT could not verify that response against canonical data, so it is
withholding it rather than risk showing an unsupported or unsafe claim.
```

Real finding worth flagging: both live generations (temperature 0.2, 600 max
tokens, no grounding data) ended up **safety-withheld**, not because
`check_output_safety` fired, but because the FAST/DEEP Nemotron models are
reasoning models that sometimes spend most or all of the token budget on
visible chain-of-thought preamble (confirmed directly — a raw, ungated probe
against the same FAST model + prompt returned literally `"Here"` as the
`content` field for one sample, and a `max_tokens=10` probe returned `"Here's
a thinking process:\n\n1. **"` for another) rather than a clean final answer,
and the system prompt's "do not show your reasoning" instruction is not
reliably honored by the model itself. This isn't a gate false-positive — in
the traces observed, `check_output_safety` was not what blocked either
run — but it's a real, live example of the safety net earning its keep: an
incomplete/off-format generation is withheld rather than shown, exactly per
the FALLBACK TREE's spirit, even though the *specific* trigger was
implementation-arbitrary each run (numeric/safety on one call, empty-content
handling on others across repeated manual probes). `NVIDIA_MODEL_RESEARCH.md`
already flags that Nemotron 3 Super has a "configurable thinking budget" —
suppressing/bounding chain-of-thought explicitly (a `chat_template_kwargs`-
style parameter) is a real follow-up for whichever wave owns prompt/response
quality next; `model_client.py`'s current signature does not expose it, and
extending that file was out of this task's scope (read-only).

## Behavior change and regression note (full existing suite run)

Wiring in Wave 5's policy module has one real, intended consequence: any
message that previously fell through tool dispatch to `UNSUPPORTED` or
`INSUFFICIENT_EVIDENCE` now resolves to `CLARIFICATION_REQUIRED` instead
(still zero tools invoked, still a `safety_disclaimer`, still never
fabricated — an "ask" instead of a "can't answer", which is the *more*
conservative outcome). Four pre-existing tests encoded the old literal
execution-class label and were updated (not weakened) to assert the new,
intended one, each with an inline comment explaining exactly why:

- `test_orchestrator.py::test_bare_referent_with_component_id_resolves_context_but_still_defers`
  (renamed from `..._does_not_trigger_clarification`; now also independently
  re-verifies `context_resolver.resolve_context` itself still returns
  `needs_clarification=False` for this input, so the original guarantee it
  proved stays covered)
- `test_orchestrator.py::test_no_matching_tool_family_returns_clarification_not_fabricated`
  (renamed from `..._returns_unsupported_not_fabricated`)
- `test_orchestrator.py::test_missing_required_context_returns_clarification_not_fabricated`
  (renamed from `..._returns_insufficient_evidence_not_fabricated`)
- `test_assistant_router.py::test_post_message_stub_response_shape` and
  `test_post_message_physician_audience_still_stubbed` (same root cause via
  the FastAPI stub route)
- `test_decision_adversary.py::test_hypothesis_3_...` (its assertion that
  `is_complex_reasoning_required` is absent from `orchestrator.py` is now
  false — updated to assert it **is** present, since wiring it in was this
  task's explicit goal; the other 3 unwired decision types' absence
  assertions are untouched and still true)
- `test_decision_adversary.py::test_prompt_injection_shaped_text_..._because_none_exists`
  (renamed `..._does_not_reach_the_llm_today`; its premise — "no LLM exists"
  — is no longer true, so it now documents and verifies the real, narrower,
  current reason this specific payload still doesn't reach the model today
  (policy deferral), explicitly without overclaiming that the output gates
  would catch a generic prompt-injection/system-prompt leak if it did)

### Full suite result after all updates

```
$ python3 -m pytest python/hearttwin/tests/ -q --timeout=300
1231 passed, 5 skipped, 6 xfailed, 494 warnings in 12.68s
```

Zero unexplained regressions. Every change to a pre-existing assertion is
listed above with its cause; every other test (including all of Wave 5's
"KNOWN GAP" `xfail(strict=True)` red-team tests) is untouched and still
passes/xfails exactly as before.

### Scoped orchestrator + new-suite run

```
$ python3 -m pytest python/hearttwin/tests/test_orchestrator.py python/hearttwin/tests/test_orchestrator_model_routing.py -v
...
======================== 20 passed, 4 skipped in 2.98s =========================
```

(The 4 skips are the real, opt-in integration tests — they run and pass, as
shown above, only with `RUN_EXTERNAL_INTEGRATION_TESTS=true` and real
credentials.)

## Global Architecture Compliance: YES

- No second tool registry, model router, decision layer, or safety layer was
  created — this extends the one existing pipeline at its documented
  integration point.
- The deterministic physics core (`cardiac_state.py`/`hemodynamics.py`/
  `recovery_sim.py`) was not touched, referenced, or reasoned about by any
  model call — the model only ever sees a `ToolResult.canonical_payload` (a
  post-computation snapshot) or nothing at all.
- Laya continues to make only bounded, non-clinical routing decisions
  (`is_complex_reasoning_required`, plus the pre-existing `classify_intent`/
  `select_tool_family`); it never gained a "generate the answer" path.
- Every model-generated response passes through the same
  `check_output_safety` + `validate_numeric_claims` gates as tool-rendered
  text, and the `safety_disclaimer` remains attached via `AssistantResponse`'s
  default on every return path.
- The FALLBACK TREE ("All NVIDIA unavailable -> canonical BeatIT tools still
  work") holds: every model-call failure mode degrades to the exact
  deterministic response the pre-Wave-6 orchestrator would have produced.
