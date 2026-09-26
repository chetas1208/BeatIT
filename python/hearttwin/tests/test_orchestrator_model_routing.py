"""Tests for the Wave 6 MODEL ROUTER extension to orchestrator.py.

See python/hearttwin/assistant/orchestrator.py's module docstring point (g)
for the full decision tree this file exercises: laya_policy's classify_intent
deferral gate -> FAST/DEEP selection (LayaAdapter.is_complex_reasoning_
required) -> tool-grounded (or explicitly not) prompt -> a real
model_client.chat_completion call -> the same output-safety/numeric-claim
gates (e) already runs on tool-rendered text -> a deterministic fallback on
ANY failure.

Two tiers, per this wave's task brief:

  * Mocked unit tests (the large majority; no network, no cost) — branch
    selection, the Wave 5 policy-deferral wiring, the safety/numeric
    fallback, and the model-call-failure fallback.
  * A small number of REAL, opt-in integration tests that make genuine HTTP
    calls to the configured NVIDIA endpoint through the actual
    ``model_client.chat_completion``. Gated behind ``RUN_EXTERNAL_
    INTEGRATION_TESTS`` (the same env var ``test_weave_integration.py``
    already uses for this repo's other real-external-API tests — reused here
    rather than inventing a second, competing opt-in flag) so a normal
    ``pytest`` run never burns money or needs live credentials.

IMPORTANT, read before puzzling over any "why is this CLARIFICATION_REQUIRED
and not GENERATIVE_EXPLANATION" test: laya_policy.py's classify_intent
decision type measured 58.6% accuracy against BeatIT's own fixtures — below
its own 70% trust threshold — so
``laya_policy.should_defer_to_clarification("classify_intent", ...)``
currently returns True unconditionally, for every source ("laya" or
"fallback") and every message. That means, as of today's measured numbers,
the live orchestrator ALWAYS prefers the conservative clarification response
over a real model call whenever no tool matched. This is the intended,
documented Wave 6 behavior (see orchestrator.py's module docstring and
docs/assistant/wave6/model-router.md) — proof that Wave 5's policy module is
now actually consulted in the live path, not just imported and ignored. Every
test below that needs to reach *past* that gate to exercise FAST/DEEP
selection or a real model call does so by explicitly monkeypatching
``should_defer_to_clarification`` to ``False`` at the orchestrator's own
import site, with a comment saying so — never by pretending the gate doesn't
exist.
"""

from __future__ import annotations

import os
from datetime import datetime

import pytest

from python.hearttwin.assistant.laya_adapter import LayaAdapter
from python.hearttwin.assistant.model_client import ModelClientError, ChatCompletionResult
from python.hearttwin.assistant.model_pool import ModelRole, get_model_id
from python.hearttwin.assistant.orchestrator import (
    _CLARIFICATION_MESSAGE,
    _UNSAFE_OUTPUT_FALLBACK_MESSAGE,
    _build_model_messages,
    _generate_model_response,
    handle_message,
)
from python.hearttwin.assistant.schemas import (
    AssistantRequest,
    ConversationContext,
    ExecutionClass,
    ToolResult,
)
from python.hearttwin.assistant.tool_registry import get_tool_registry
from python.hearttwin.ensemble import (
    PARAMETER_BOUNDS,
    EnsembleDistributionRequest,
    EnsembleRequest,
    run_ensemble,
)
from python.hearttwin.schemas import CardiacTwinState, Hemodynamics, MeasuredValue, Measurements, ValueSource
from python.hearttwin.storage.ensemble_store import create_ensemble_store

_ORCH = "python.hearttwin.assistant.orchestrator"

_BASE_CONTEXT_KWARGS = dict(conversation_id="conv-model-router", audience="general")


def _context(**overrides) -> ConversationContext:
    return ConversationContext(**{**_BASE_CONTEXT_KWARGS, **overrides})


def _request(message: str, context: ConversationContext) -> AssistantRequest:
    return AssistantRequest(conversation_id=context.conversation_id, message=message, context=context)


def _fake_result(text: str) -> ChatCompletionResult:
    return ChatCompletionResult(text=text, model="fake-model", latency_ms=1.0, key_used="slot-1")


# ---------------------------------------------------------------------------
# Messages engineered to hit the "no tool matched" branch (tool_result is
# None -> the MODEL ROUTER) without tripping the earlier context-resolution
# bare-referent short-circuit ("this"/"that"/"it"/"here") or Laya's own
# CLARIFICATION_REQUIRED intent classification. See laya_adapter.py's
# fallback keyword lists for exactly which words route where.
# ---------------------------------------------------------------------------

_SIMPLE_MESSAGE = "Tell me something interesting."  # -> family NONE, intent GENERATIVE_EXPLANATION, simple (FAST)
_COMPLEX_MESSAGE = (
    "Please compare the directly observed measurements against the derived "
    "estimates and summarize which findings are more reliable overall across "
    "the entire modeling pipeline for future reference."
)  # -> family COMPARE (0 registered tools), intent COMPLEX_SYNTHESIS, complex (DEEP)


# ---------------------------------------------------------------------------
# _build_model_messages — pure prompt-construction unit tests
# ---------------------------------------------------------------------------


def test_build_model_messages_without_tool_result_forbids_fabrication() -> None:
    context = _context()
    messages = _build_model_messages("What is the current EF?", context, tool_result=None)

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "GROUNDING DATA: none available" in messages[1]["content"]
    assert "What is the current EF?" in messages[1]["content"]


def test_build_model_messages_with_tool_result_includes_real_payload() -> None:
    context = _context(ensemble_id="ens-123")
    tool_result = ToolResult(
        tool_name="get_ensemble",
        execution_class=ExecutionClass.EVIDENCE_RETRIEVAL,
        canonical_payload={"id": "ens-123", "samples": [1, 2, 3]},
        safety_level="T0",
    )

    messages = _build_model_messages("What does this ensemble show?", context, tool_result=tool_result)

    content = messages[1]["content"]
    assert "GROUNDING DATA (canonical, real, from BeatIT tool 'get_ensemble'" in content
    assert "ens-123" in content


# ---------------------------------------------------------------------------
# Wave 5 policy module — first real production consultation
# ---------------------------------------------------------------------------


async def test_policy_deferral_prevents_model_call_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """No mocking of the policy itself: proves the REAL laya_policy verdict
    (classify_intent is not trustworthy, measured 58.6% < 70%) is consulted
    on the live path and wins over ever calling the model — zero network
    cost, since chat_completion must never even be reached."""
    called = False

    async def _should_not_be_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("chat_completion must not be called when the policy defers")

    monkeypatch.setattr(f"{_ORCH}.chat_completion", _should_not_be_called)

    context = _context()
    request = _request(_SIMPLE_MESSAGE, context)

    response = await handle_message(request)

    assert called is False
    assert response.execution_class == ExecutionClass.CLARIFICATION_REQUIRED
    assert response.message == _CLARIFICATION_MESSAGE
    assert response.trace.tools_invoked == []
    assert response.trace.model_used is None


async def test_policy_module_consulted_with_the_actual_decision_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spies on should_defer_to_clarification (delegating to the real
    implementation) to prove the orchestrator calls it with the exact
    ("classify_intent", <real decision source>) arguments laya_policy.py
    documents as its intended integration point — not a stub, not ignored."""
    from python.hearttwin.assistant.laya_policy import should_defer_to_clarification as real_policy

    calls: list[tuple[str, str]] = []

    def _spy(decision_name: str, decision_source: str, **kwargs):
        calls.append((decision_name, decision_source))
        return real_policy(decision_name, decision_source, **kwargs)

    monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", _spy)

    context = _context()
    request = _request(_SIMPLE_MESSAGE, context)
    response = await handle_message(request)

    assert calls == [("classify_intent", "fallback")]
    assert response.execution_class == ExecutionClass.CLARIFICATION_REQUIRED


# ---------------------------------------------------------------------------
# FAST vs DEEP branch selection (policy gate forced open to reach it)
# ---------------------------------------------------------------------------


async def test_simple_request_routes_to_fast_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

    captured: dict = {}

    async def _fake_chat_completion(messages, model, **kwargs):
        captured["model"] = model
        return _fake_result("BeatIT helps you explore a simulated cardiac twin.")

    monkeypatch.setattr(f"{_ORCH}.chat_completion", _fake_chat_completion)

    context = _context()
    request = _request(_SIMPLE_MESSAGE, context)
    response = await handle_message(request)

    assert captured["model"] == get_model_id(ModelRole.FAST)
    assert response.execution_class == ExecutionClass.GENERATIVE_EXPLANATION
    assert response.trace.model_used == get_model_id(ModelRole.FAST)
    assert response.message == "BeatIT helps you explore a simulated cardiac twin."


async def test_complex_request_routes_to_deep_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

    captured: dict = {}

    async def _fake_chat_completion(messages, model, **kwargs):
        captured["model"] = model
        return _fake_result("General orientation only; ask for a specific ensemble to compare.")

    monkeypatch.setattr(f"{_ORCH}.chat_completion", _fake_chat_completion)

    context = _context()
    request = _request(_COMPLEX_MESSAGE, context)
    response = await handle_message(request)

    assert captured["model"] == get_model_id(ModelRole.DEEP)
    assert response.execution_class == ExecutionClass.COMPLEX_SYNTHESIS
    assert response.trace.model_used == get_model_id(ModelRole.DEEP)


# ---------------------------------------------------------------------------
# Output rail on generated text — same gates (e) already runs, extended here
# ---------------------------------------------------------------------------


async def test_safety_violation_falls_back_to_safe_generic_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

    async def _unsafe_chat_completion(messages, model, **kwargs):
        return _fake_result("I recommend you take medication and prescribe a new plan.")

    monkeypatch.setattr(f"{_ORCH}.chat_completion", _unsafe_chat_completion)

    context = _context()
    request = _request(_SIMPLE_MESSAGE, context)
    response = await handle_message(request)

    assert response.message == _UNSAFE_OUTPUT_FALLBACK_MESSAGE
    assert response.execution_class == ExecutionClass.GENERATIVE_EXPLANATION
    # model_used is still recorded — the call succeeded, only its content was withheld.
    assert response.trace.model_used == get_model_id(ModelRole.FAST)


async def test_unguarded_numeric_claim_falls_back_to_safe_generic_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """Structural enforcement of the tool-first rule: no ToolResult ran this
    turn, so canonical_payload is {} — ANY numeric cardiac claim the model
    makes is therefore unsupported by definition, regardless of prompt
    wording, and validate_numeric_claims rejects it."""
    monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

    async def _fabricating_chat_completion(messages, model, **kwargs):
        return _fake_result("Your ejection fraction is 45%.")

    monkeypatch.setattr(f"{_ORCH}.chat_completion", _fabricating_chat_completion)

    context = _context()
    request = _request(_SIMPLE_MESSAGE, context)
    response = await handle_message(request)

    assert response.message == _UNSAFE_OUTPUT_FALLBACK_MESSAGE


async def test_empty_model_response_falls_back_to_safe_generic_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

    async def _empty_chat_completion(messages, model, **kwargs):
        return _fake_result("   ")

    monkeypatch.setattr(f"{_ORCH}.chat_completion", _empty_chat_completion)

    context = _context()
    request = _request(_SIMPLE_MESSAGE, context)
    response = await handle_message(request)

    assert response.message == _UNSAFE_OUTPUT_FALLBACK_MESSAGE


# ---------------------------------------------------------------------------
# Model-call failure -> deterministic fallback (FALLBACK TREE)
# ---------------------------------------------------------------------------


async def test_model_client_error_falls_back_to_deterministic_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

    async def _raising_chat_completion(messages, model, **kwargs):
        raise ModelClientError("simulated: all keys exhausted")

    monkeypatch.setattr(f"{_ORCH}.chat_completion", _raising_chat_completion)

    context = _context()
    request = _request(_SIMPLE_MESSAGE, context)
    response = await handle_message(request)

    # _SIMPLE_MESSAGE routes to family NONE -> the plain "no lookup needed"
    # UNSUPPORTED text _select_and_execute_tool already produces (d) — the
    # exact response handle_message would have returned pre-Wave-6.
    assert response.execution_class == ExecutionClass.UNSUPPORTED
    assert response.trace.tools_invoked == []
    assert response.trace.model_used is None
    assert response.message == "This request doesn't require a lookup from one of BeatIT's canonical tools."


async def test_unexpected_exception_during_model_call_never_crashes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Belt-and-suspenders: even a non-ModelClientError exception must
    degrade gracefully, never propagate out of the orchestrator."""
    monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

    async def _weird_failure(messages, model, **kwargs):
        raise RuntimeError("totally unexpected")

    monkeypatch.setattr(f"{_ORCH}.chat_completion", _weird_failure)

    context = _context()
    request = _request(_SIMPLE_MESSAGE, context)
    response = await handle_message(request)  # must not raise

    assert response.execution_class == ExecutionClass.UNSUPPORTED
    assert response.trace.tools_invoked == []


# ---------------------------------------------------------------------------
# REAL, opt-in integration tests — genuine NVIDIA API calls.
#
# Disabled by default; enable with:
#   RUN_EXTERNAL_INTEGRATION_TESTS=true pytest python/hearttwin/tests/test_orchestrator_model_routing.py
# and MODEL_API_KEY_1 (or _2/_3) set to a real NVIDIA Build key in the
# environment (this repo's existing convention for real-external-API tests —
# see test_weave_integration.py — is that credentials come from the
# environment, never loaded by the test itself).
# ---------------------------------------------------------------------------

EXTERNAL = os.environ.get("RUN_EXTERNAL_INTEGRATION_TESTS", "").lower() in {"1", "true", "yes"}
_EXTERNAL_REASON = (
    "real NVIDIA model-router integration disabled "
    "(set RUN_EXTERNAL_INTEGRATION_TESTS=true and configure MODEL_API_KEY_1..3)"
)


def _measured(value: float, unit: str) -> MeasuredValue:
    return MeasuredValue(value=value, unit=unit, source=ValueSource.FILE_EXTRACTION, confidence=1.0)


def _state(baseline_vitals: dict) -> CardiacTwinState:
    return CardiacTwinState(
        case_id="model-router-fixture-case",
        created_at=datetime(2026, 1, 2, 3, 4, 5),  # noqa: DTZ001 - canonical naive fixture timestamp
        measurements=Measurements(
            heart_rate_bpm=_measured(baseline_vitals["heart_rate_bpm"], "bpm"),
            systolic_bp_mmhg=_measured(baseline_vitals["systolic_bp_mmhg"], "mmHg"),
            diastolic_bp_mmhg=_measured(baseline_vitals["diastolic_bp_mmhg"], "mmHg"),
            edv_ml=_measured(baseline_vitals["edv_ml"], "mL"),
            esv_ml=_measured(baseline_vitals["esv_ml"], "mL"),
        ),
        hemodynamics=Hemodynamics(
            preload_index=_measured(1.0, "index"),
            afterload_index=_measured(1.0, "index"),
            contractility_index=_measured(1.0, "index"),
            systemic_vascular_resistance_index=_measured(1.0, "index"),
        ),
    )


def _distribution(parameter_id: str) -> EnsembleDistributionRequest:
    defaults: dict[str, tuple[dict, dict]] = {
        "heart_rate_bpm": ({"mean": 72.0, "sd": 2.0}, {"min": 30.0, "max": 200.0}),
        "preload_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 1.5}),
        "afterload_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 2.0}),
        "contractility_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 1.5}),
        "systemic_vascular_resistance_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 2.0}),
    }
    parameters, bounds = defaults[parameter_id]
    return EnsembleDistributionRequest(
        parameter_id=parameter_id,
        family="normal",
        parameters=parameters,
        bounds=bounds,
        source="measurement",
        evidence_ids=["manual_baseline.json"],
        rationale="Model-router integration test fixture",
        version="test-v1",
    )


@pytest.fixture
def persisted_ensemble(baseline_vitals: dict, tmp_path, monkeypatch) -> dict:
    monkeypatch.setenv("BEATIT_ENSEMBLE_DB_PATH", str(tmp_path / "ensembles.sqlite3"))
    request = EnsembleRequest(
        origin_snapshot_id="snapshot-model-router",
        state=_state(baseline_vitals),
        seed=11,
        sample_count=6,
        distributions=[_distribution(parameter_id) for parameter_id in PARAMETER_BOUNDS],
        origin_quality="observed",
    )
    result = run_ensemble(request)
    create_ensemble_store().save(result["id"], result)
    return result


@pytest.mark.skipif(not EXTERNAL, reason=_EXTERNAL_REASON)
class TestRealModelRouterIntegration:
    """Genuine, billed calls to the configured NVIDIA endpoint.

    Each test forces `should_defer_to_clarification` open (see module
    docstring "IMPORTANT" note above): with today's measured classify_intent
    accuracy the live policy always defers before reaching the model, so an
    end-to-end proof that the model call itself works requires deliberately
    stepping past that gate. The deferral path itself is proven for real,
    at zero network cost, by test_policy_deferral_prevents_model_call_by_default.
    """

    async def test_real_fast_model_end_to_end_through_handle_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

        context = _context()
        request = _request(_SIMPLE_MESSAGE, context)

        response = await handle_message(request)

        assert response.trace.tools_invoked == []
        assert response.safety_disclaimer
        assert response.execution_class == ExecutionClass.GENERATIVE_EXPLANATION
        assert response.trace.model_used == get_model_id(ModelRole.FAST)
        assert response.message  # never empty — real content or the safe fallback text

    async def test_real_deep_model_end_to_end_through_handle_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

        context = _context()
        request = _request(_COMPLEX_MESSAGE, context)

        response = await handle_message(request)

        assert response.trace.tools_invoked == []
        assert response.safety_disclaimer
        assert response.execution_class == ExecutionClass.COMPLEX_SYNTHESIS
        assert response.trace.model_used == get_model_id(ModelRole.DEEP)
        assert response.message

    async def test_real_model_call_grounds_response_in_real_tool_result(
        self, persisted_ensemble: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Enters below handle_message, at _generate_model_response directly,
        with a real ToolResult built from a real, persisted ensemble.

        Documented, honest gap (matches this file's own style elsewhere):
        under today's tool registry + tool-dispatch logic, handle_message
        never reaches the MODEL ROUTER with a non-None tool_result (the
        branch only triggers when NO tool matched — see orchestrator.py's
        module docstring point (g)), so there is currently no full
        handle_message() path that exercises the tool-grounded prompt for
        real. This test proves the grounding + validation logic itself works
        against a real model response, calling the same function
        handle_message would call if that trigger condition is ever widened.
        """
        monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)

        context = _context(ensemble_id=persisted_ensemble["id"])
        request = _request("Explain what this ensemble shows about uncertainty.", context)
        laya = LayaAdapter()
        intent_decision = await laya.classify_intent(request.message, request.context.model_dump())
        tool_result = ToolResult(
            tool_name="get_ensemble",
            execution_class=ExecutionClass.EVIDENCE_RETRIEVAL,
            canonical_payload={
                "id": persisted_ensemble["id"],
                "sample_count": len(persisted_ensemble["samples"]),
            },
            safety_level="T0",
        )

        response = await _generate_model_response(
            request,
            laya,
            intent_decision,
            tool_result=tool_result,
            fallback_response_text="FALLBACK_SHOULD_NOT_APPEAR",
            fallback_execution_class=ExecutionClass.UNSUPPORTED,
        )

        assert response.trace.tools_invoked == ["get_ensemble"]
        assert response.trace.model_used is not None
        assert response.message != "FALLBACK_SHOULD_NOT_APPEAR"

    async def test_real_model_failure_falls_back_to_deterministic_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Forces a genuine API failure (an invalid model id against the real
        endpoint, not a mock) to prove the FALLBACK TREE against a real
        NVIDIA error response, not a simulated one."""
        monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)
        monkeypatch.setattr(
            f"{_ORCH}.get_model_id",
            lambda role: "nvidia/this-model-id-does-not-exist-beatit-wave6-test",
        )

        context = _context()
        request = _request(_SIMPLE_MESSAGE, context)

        response = await handle_message(request)

        assert response.execution_class == ExecutionClass.UNSUPPORTED
        assert response.trace.tools_invoked == []
        assert response.trace.model_used is None
        assert response.message == "This request doesn't require a lookup from one of BeatIT's canonical tools."
