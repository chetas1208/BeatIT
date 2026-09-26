"""Request-handling pipeline for the unified BeatIT conversation assistant (Wave 3).

Wires together, in order, the pieces Wave 2 built in isolation
(``laya_adapter.py``, ``tool_registry.py``, ``safety_validator.py``) plus
Wave 3's ``context_resolver.py`` into one real pipeline, per
docs/assistant/GLOBAL_ARCHITECTURE.md's "TOP-LEVEL ARCHITECTURE":

    INPUT VALIDATION -> ... -> SAFETY / POLICY -> SYSTEM-1 (Laya) ->
    EXECUTION POLICY -> TOOL CALL -> ... -> RESPONSE ASSEMBLER ->
    (NUMERIC / SAFETY validators) -> BEATIT COPILOT

Concretely, ``handle_message`` runs:

  (a) ``safety_validator.classify_request_safety`` — input rail. Blocked
      requests (emergency/diagnosis/treatment) return immediately. This runs
      BEFORE context resolution and BEFORE Laya on purpose: a request that
      must be blocked is blocked regardless of what "this" refers to, and
      Laya (System-1) is explicitly barred from clinical-safety authority
      per GLOBAL_ARCHITECTURE.md ("SYSTEM-1 (Laya) VS SYSTEM-2") — safety
      must never depend on, or be reachable only after, a routing decision.
  (b) ``context_resolver.resolve_context`` — if the message can't be safely
      routed against the current ConversationContext, short-circuit to
      CLARIFICATION_REQUIRED rather than guessing a referent.
  (c) ``LayaAdapter.classify_intent`` + ``select_tool_family`` — System-1
      routing signals.
  (d) Tool dispatch: pick a registered tool in the selected family whose
      required input-schema fields are all present in context, execute it
      via ``ToolRegistry``, and render a deterministic response straight
      from its real ``ToolResult`` payload. No LLM call is made anywhere in
      this wave (see module-level note below) — if no tool's requirements
      are met, this returns an honest INSUFFICIENT_EVIDENCE/UNSUPPORTED
      response instead of fabricating an answer.
  (e) Output rail: ``check_output_safety`` always, ``validate_numeric_claims``
      against the tool's own canonical payload whenever a tool ran. Either
      failing falls back to a generic, safe response instead of the
      generated text.
  (f) The safety disclaimer is always attached — ``AssistantResponse``
      defaults ``safety_disclaimer`` to the canonical ``DISCLAIMER``
      (schemas.py), so every return path below gets it for free.

No LLM / model-router integration exists in this wave. Wave 2 built
``model_pool.py`` (a key pool) but no chat-completion client, and building
one is explicitly out of this agent's scope (docs/assistant/WAVE_2_HANDOFF.md
"Known failures": "no chat-completion client exists yet"). Every response
this module produces is therefore deterministic: either a safety/
clarification short-circuit, or text rendered directly from a real
ToolResult payload. GENERATIVE_EXPLANATION / COMPLEX_SYNTHESIS execution
classes cannot actually be fulfilled yet — a request that Laya routes there
falls through the same "no matching tool" path as any other unsupported
family, which is correct: this wave must never pretend to reason when it
cannot.
"""

from __future__ import annotations

from typing import Any, Optional

from python.hearttwin.assistant.context_resolver import resolve_context
from python.hearttwin.assistant.laya_adapter import LayaAdapter
from python.hearttwin.assistant.safety_validator import (
    RequestSafetyDecision,
    check_output_safety,
    classify_request_safety,
    validate_numeric_claims,
)
from python.hearttwin.assistant.schemas import (
    AssistantRequest,
    AssistantResponse,
    AssistantTraceMeta,
    ConversationContext,
    ExecutionClass,
)
from python.hearttwin.assistant.tool_registry import (
    Tool,
    ToolExecutionError,
    ToolRegistry,
    ToolResult,
    get_tool_registry,
)

# Generic, non-clinical copy used whenever a real answer has to be withheld.
# Never includes any tool payload content, so it can never itself trip the
# output-safety/numeric gates it's a fallback for.
_CLARIFICATION_MESSAGE = (
    "Could you clarify what you mean? I don't have enough context yet (e.g. a "
    "selected component, snapshot, ensemble, or scenario) to answer that safely."
)
_UNSAFE_OUTPUT_FALLBACK_MESSAGE = (
    "BeatIT could not verify that response against canonical data, so it is "
    "withholding it rather than risk showing an unsupported or unsafe claim."
)

# UNCERTAINTY-family disambiguation: when more than one registered tool in a
# family could answer, prefer the one whose keyword the user actually used
# rather than always returning the same (first-registered) tool. Order
# matters: checked top to bottom, first match wins.
_TOOL_NAME_KEYWORD_PREFERENCE: tuple[tuple[str, str], ...] = (
    ("assumption", "get_ensemble_assumptions"),
    ("distribution", "get_ensemble_distributions"),
)


def _safety_blocked_response(decision: RequestSafetyDecision) -> AssistantResponse:
    message = decision.reason or (
        "BeatIT cannot help with this request. It supports educational cardiac "
        "simulation and report organization only — it does not make emergency, "
        "diagnostic, or treatment decisions. A qualified human must make that call."
    )
    return AssistantResponse(
        message=message,
        # GLOBAL_ARCHITECTURE.md: emergency/diagnosis/treatment are T3-territory
        # ("NOT ordinary BeatIT tools ... support human decision-making instead"),
        # which is exactly what HUMAN_DECISION_REQUIRED denotes.
        execution_class=ExecutionClass.HUMAN_DECISION_REQUIRED,
        trace=AssistantTraceMeta(tools_invoked=[]),
    )


def _clarification_response() -> AssistantResponse:
    return AssistantResponse(
        message=_CLARIFICATION_MESSAGE,
        execution_class=ExecutionClass.CLARIFICATION_REQUIRED,
        trace=AssistantTraceMeta(tools_invoked=[]),
    )


def _preferred_tool_name(tool_family: str, message: str) -> Optional[str]:
    if tool_family != "UNCERTAINTY":
        return None
    normalized = (message or "").lower()
    for keyword, name in _TOOL_NAME_KEYWORD_PREFERENCE:
        if keyword in normalized:
            return name
    return None


def _resolve_required_args(tool: Tool, context_dict: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Match a tool's required input-schema fields against context by name.

    Deliberately generic rather than a per-tool-name special case: a tool is
    only a real candidate when every argument name it requires (e.g.
    "ensemble_id") is also a non-None field on ConversationContext with the
    same name. This is why `get_cardiac_findings` (requires "case_id") stays
    unreachable this wave — ConversationContext has no `case_id` field, only
    `patient_id` — rather than silently guessing patient_id is a case_id.
    That gap is a real, honest limitation (see design note), not a bug to
    paper over here.
    """
    required = tool.input_schema.get("required", [])
    args = {field: context_dict.get(field) for field in required}
    if any(value is None for value in args.values()):
        return None
    return args


async def _select_and_execute_tool(
    registry: ToolRegistry,
    tool_family: str,
    message: str,
    context: ConversationContext,
) -> tuple[Optional[ToolResult], str, ExecutionClass]:
    if tool_family == "NONE":
        return (
            None,
            "This request doesn't require a lookup from one of BeatIT's canonical tools.",
            ExecutionClass.UNSUPPORTED,
        )

    candidates = registry.list_tools(category=tool_family)
    if not candidates:
        return (
            None,
            f"BeatIT does not yet have a tool in the {tool_family} category to answer this request.",
            ExecutionClass.UNSUPPORTED,
        )

    preferred_name = _preferred_tool_name(tool_family, message)
    ordered = candidates
    if preferred_name is not None:
        ordered = sorted(candidates, key=lambda tool: tool.name != preferred_name)

    context_dict = context.model_dump()
    chosen_tool: Optional[Tool] = None
    chosen_args: dict[str, Any] = {}
    for tool in ordered:
        args = _resolve_required_args(tool, context_dict)
        if args is not None:
            chosen_tool = tool
            chosen_args = args
            break

    if chosen_tool is None:
        return (
            None,
            (
                f"BeatIT has a {tool_family.lower()} tool that could answer this, but the "
                "current conversation is missing the identifier it needs (e.g. a "
                "selected ensemble or case) — insufficient evidence to answer without it."
            ),
            ExecutionClass.INSUFFICIENT_EVIDENCE,
        )

    try:
        result = await registry.execute(chosen_tool.name, **chosen_args)
    except ToolExecutionError as exc:
        return (
            None,
            f"BeatIT could not retrieve that data: {exc}",
            ExecutionClass.INSUFFICIENT_EVIDENCE,
        )

    return result, _render_tool_result(chosen_tool.name, result), result.execution_class


def _render_tool_result(tool_name: str, result: ToolResult) -> str:
    """Deterministic text straight from a real ToolResult payload — no LLM.

    Kept intentionally plain (counts/keys/labels, not narrative prose) so it
    can never itself introduce a numeric claim the payload doesn't support.
    """
    payload = result.canonical_payload
    if tool_name == "get_ensemble":
        sample_count = len(payload.get("samples", []) or [])
        return f"Ensemble {payload.get('id')} has {sample_count} recorded sample(s)."
    if tool_name == "get_ensemble_distributions":
        metrics = sorted((payload.get("distributions") or {}).keys())
        metrics_text = ", ".join(metrics) if metrics else "none recorded"
        return f"Recorded output-metric distributions for ensemble {payload.get('ensemble_id')}: {metrics_text}."
    if tool_name == "get_ensemble_assumptions":
        assumptions = payload.get("assumptions") or []
        if not assumptions:
            return f"No explicit modeling assumptions are recorded for ensemble {payload.get('ensemble_id')}."
        joined = " ".join(assumptions)
        return f"Recorded modeling assumptions for ensemble {payload.get('ensemble_id')}: {joined}"
    if tool_name == "get_cardiac_findings":
        findings = ((payload.get("cardiac_findings") or {}).get("findings")) or []
        return f"{len(findings)} cardiac finding(s) recorded for case {payload.get('case_id')}."
    return f"Retrieved data from {tool_name}."


async def handle_message(
    request: AssistantRequest,
    *,
    laya: Optional[LayaAdapter] = None,
    registry: Optional[ToolRegistry] = None,
) -> AssistantResponse:
    """The one real request-handling pipeline for the unified assistant.

    ``laya``/``registry`` are injectable purely for tests; production callers
    (``router.py``) omit them and get the process-wide tool registry
    singleton and a fresh, stateless LayaAdapter.
    """
    laya = laya or LayaAdapter()
    registry = registry or get_tool_registry()

    # (a) safety-first — see module docstring for why this runs before
    # context resolution and before any Laya call.
    safety_decision = classify_request_safety(request.message)
    if safety_decision.blocked:
        return _safety_blocked_response(safety_decision)

    # (b) context resolution / clarification gate
    resolution = await resolve_context(request.message, request.context, laya=laya)
    if resolution.needs_clarification:
        return _clarification_response()

    # (c) System-1 routing signals
    intent_decision = await laya.classify_intent(request.message, request.context.model_dump())
    if intent_decision.chosen == ExecutionClass.CLARIFICATION_REQUIRED.value:
        # Laya's own intent classifier can independently flag ambiguity that
        # needs_clarification's bare-referent heuristic doesn't catch (e.g. a
        # near-empty message with no pronoun at all) — same short-circuit.
        return _clarification_response()
    family_decision = await laya.select_tool_family(request.message, request.context.model_dump())

    # (d) tool dispatch — deterministic, tool-result-grounded response only
    tool_result, response_text, execution_class = await _select_and_execute_tool(
        registry, family_decision.chosen, request.message, request.context
    )

    tools_invoked = [tool_result.tool_name] if tool_result is not None else []

    if tool_result is None:
        # Honest "can't answer yet" — never fabricated content, per (d).
        return AssistantResponse(
            message=response_text,
            execution_class=execution_class,
            trace=AssistantTraceMeta(tools_invoked=tools_invoked),
        )

    # (e) output rail — numeric claim gate + clinical-boundary gate
    output_decision = check_output_safety(response_text)
    numeric_result = validate_numeric_claims(response_text, tool_result.canonical_payload)
    if output_decision.blocked or not numeric_result.valid:
        return AssistantResponse(
            message=_UNSAFE_OUTPUT_FALLBACK_MESSAGE,
            execution_class=execution_class,
            trace=AssistantTraceMeta(tools_invoked=tools_invoked),
        )

    # (f) safety_disclaimer is attached automatically by AssistantResponse's default.
    return AssistantResponse(
        message=response_text,
        execution_class=execution_class,
        trace=AssistantTraceMeta(tools_invoked=tools_invoked),
    )
