"""Request-handling pipeline for the unified BeatIT conversation assistant (Wave 3-6).

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
      from its real ``ToolResult`` payload. If no tool's requirements are
      met, this used to be a dead end (Wave 3-5); Wave 6 extends it with the
      MODEL ROUTER below rather than immediately giving up.
  (e) Output rail: ``check_output_safety`` always, ``validate_numeric_claims``
      against the tool's own canonical payload whenever a tool ran (or an
      empty payload when none did — see (g)). Either failing falls back to a
      generic, safe response instead of the generated text.
  (f) The safety disclaimer is always attached — ``AssistantResponse``
      defaults ``safety_disclaimer`` to the canonical ``DISCLAIMER``
      (schemas.py), so every return path below gets it for free.
  (g) MODEL ROUTER (Wave 6, ``_generate_model_response``) — reached only when
      (d) found no matching real tool, i.e. exactly
      docs/assistant/GLOBAL_ARCHITECTURE.md's "MODEL ROUTER" first branch
      ("Can deterministic tool answer completely? NO -> ..."). This is the
      first wave that makes a real, billed NVIDIA chat-completion call:
        1. Wave 5's ``laya_policy.should_defer_to_clarification`` is
           consulted for the ``classify_intent`` decision already made in
           (c) — its own measured accuracy (58.6%, below its 70% trust
           threshold; see laya_policy.py) means this currently defers to the
           existing conservative clarification response *every* time,
           rather than ever guessing past an unreliable routing signal. This
           is deliberate: it is the first real production wiring of that
           policy module, and Wave 5's own numbers are what it acts on.
        2. Otherwise, ``LayaAdapter.is_complex_reasoning_required`` (System-1)
           picks FAST_MODEL vs DEEP_MODEL (GLOBAL_ARCHITECTURE.md "simple
           explanation? -> FAST" / "complex synthesis? -> DEEP").
        3. The prompt is tool-grounded whenever a real ``ToolResult`` is
           available at this call site; otherwise the model is explicitly
           instructed to give only general orientation/clarifying language,
           never a specific cardiac fact — GLOBAL_ARCHITECTURE.md's
           tool-first rule, enforced both by instruction AND structurally by
           step 4 (an un-grounded numeric claim has no canonical payload to
           match, so ``validate_numeric_claims`` rejects it either way).
        4. The SAME output-safety + numeric-claim gates (e) already runs on
           tool-rendered text run again here. A violation, an empty
           response, or ANY model-call failure (timeout, exhausted key pool,
           malformed response) all fall back to the plain deterministic
           response (d) would have produced without ever crashing — per
           GLOBAL_ARCHITECTURE.md's FALLBACK TREE, "All NVIDIA unavailable ->
           canonical BeatIT tools still work".
"""

from __future__ import annotations

from typing import Any, Optional

from python.hearttwin.assistant.context_resolver import resolve_context
from python.hearttwin.assistant.laya_adapter import ChoiceDecision, LayaAdapter
from python.hearttwin.assistant.laya_policy import should_defer_to_clarification
from python.hearttwin.assistant.model_client import ModelClientError, chat_completion
from python.hearttwin.assistant.model_pool import ModelRole, get_model_id
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

# ---------------------------------------------------------------------------
# (g) MODEL ROUTER (Wave 6) — see module docstring for the full decision tree.
# ---------------------------------------------------------------------------

_MODEL_MAX_TOKENS = 600
_MODEL_TEMPERATURE = 0.2
_MODEL_TIMEOUT_SECONDS = 45.0

# GLOBAL_ARCHITECTURE.md's tool-first rule, spelled out for the model itself
# (belt-and-suspenders alongside the structural enforcement in
# _generate_model_response: an ungrounded numeric claim always fails
# validate_numeric_claims against an empty canonical payload regardless of
# what the model was told).
_MODEL_SYSTEM_PROMPT = (
    "You are the System-2 explanation layer of BeatIT, an educational cardiac "
    "digital twin assistant. You NEVER diagnose, prescribe, recommend "
    "treatment, or give emergency guidance — a qualified human always makes "
    "those calls. You NEVER state or imply a specific numeric cardiac "
    "measurement (ejection fraction/EF, stroke volume/SV, cardiac output/CO, "
    "mean arterial pressure/MAP, heart rate/HR, EDV, ESV, QTc, or any other "
    "patient-specific number) unless that exact figure is given to you below "
    "under GROUNDING DATA. If no GROUNDING DATA is provided, give only brief, "
    "general orientation about cardiac physiology concepts or BeatIT's "
    "capabilities, or ask a clarifying question — never state or imply a "
    "specific patient finding. Do not show your reasoning steps; answer "
    "directly in 2-4 sentences."
)


def _build_model_messages(
    message: str,
    context: ConversationContext,
    tool_result: Optional[ToolResult],
) -> list[dict[str, str]]:
    """Build the (system, user) messages for a Wave 6 model call.

    Grounds the prompt in a real ``ToolResult.canonical_payload`` when one is
    available at this call site; otherwise tells the model explicitly there
    is no grounding data so it must stick to general orientation — the
    tool-first rule from GLOBAL_ARCHITECTURE.md's MODEL ROUTER section.
    """
    context_lines = [f"audience: {context.audience}"]
    for field_name in (
        "product_space",
        "component_id",
        "scenario_id",
        "ensemble_id",
        "pair_id",
        "shadow_trial_id",
    ):
        value = getattr(context, field_name, None)
        if value:
            context_lines.append(f"{field_name}: {value}")

    user_parts = [
        f"User message: {message}",
        "Conversation context (non-clinical routing metadata only):\n" + "\n".join(context_lines),
    ]
    if tool_result is not None:
        user_parts.append(
            "GROUNDING DATA (canonical, real, from BeatIT tool "
            f"'{tool_result.tool_name}'; only these facts may be stated as "
            f"numbers): {tool_result.canonical_payload!r}"
        )
    else:
        user_parts.append(
            "GROUNDING DATA: none available for this turn. Do not state or "
            "imply any specific cardiac number or patient finding — general "
            "orientation or a clarifying question only."
        )

    return [
        {"role": "system", "content": _MODEL_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


async def _generate_model_response(
    request: AssistantRequest,
    laya: LayaAdapter,
    intent_decision: ChoiceDecision,
    *,
    tool_result: Optional[ToolResult],
    fallback_response_text: str,
    fallback_execution_class: ExecutionClass,
) -> AssistantResponse:
    """MODEL ROUTER second half: "Can deterministic tool answer completely? NO".

    Only called once (d) has already established the "NO" branch (no
    matching/executable tool this turn) — see module docstring point (g) for
    the full step-by-step. Never raises; every failure mode degrades to
    ``fallback_response_text``/``fallback_execution_class``, i.e. exactly the
    honest response the caller would have returned without this function.
    """
    tools_invoked = [tool_result.tool_name] if tool_result is not None else []

    # Step 1: Wave 5's policy gate on the classify_intent decision already
    # made in (c). This is the first real production call site for
    # laya_policy.should_defer_to_clarification — not merely imported.
    if should_defer_to_clarification("classify_intent", intent_decision.source):
        return _clarification_response()

    # Step 2: FAST vs DEEP, per GLOBAL_ARCHITECTURE.md's MODEL ROUTER.
    complexity_decision = await laya.is_complex_reasoning_required(
        request.message, request.context.model_dump()
    )
    role = ModelRole.DEEP if complexity_decision.answer else ModelRole.FAST
    generated_execution_class = (
        ExecutionClass.COMPLEX_SYNTHESIS if role is ModelRole.DEEP else ExecutionClass.GENERATIVE_EXPLANATION
    )
    model_id = get_model_id(role)

    # Step 3: tool-grounded (or explicitly not) prompt.
    messages = _build_model_messages(request.message, request.context, tool_result)

    # Step 4a: the real, billed NVIDIA call. Any failure (no healthy key,
    # every key's HTTP call failing, timeout, malformed body) raises a typed
    # ModelClientError — caught here and degraded to the deterministic
    # fallback, per the FALLBACK TREE ("All NVIDIA unavailable -> canonical
    # BeatIT tools still work"). The bare `except Exception` is
    # belt-and-suspenders: this function must never crash the orchestrator
    # regardless of what a future model_client change might raise.
    try:
        result = await chat_completion(
            messages,
            model_id,
            max_tokens=_MODEL_MAX_TOKENS,
            temperature=_MODEL_TEMPERATURE,
            timeout_seconds=_MODEL_TIMEOUT_SECONDS,
        )
    except ModelClientError:
        return AssistantResponse(
            message=fallback_response_text,
            execution_class=fallback_execution_class,
            trace=AssistantTraceMeta(tools_invoked=tools_invoked),
        )
    except Exception:  # noqa: BLE001 — never crash on ANY model-call failure
        return AssistantResponse(
            message=fallback_response_text,
            execution_class=fallback_execution_class,
            trace=AssistantTraceMeta(tools_invoked=tools_invoked),
        )

    # Step 4b: the SAME output rail (e) already runs on tool-rendered text.
    # canonical_payload is {} when no tool ran, which means ANY numeric
    # cardiac claim the model makes without grounding data automatically
    # mismatches (validate_numeric_claims flags an unsupported claim when the
    # metric is absent from the payload) — this is what structurally
    # enforces the tool-first / no-fabrication rule, not just the prompt.
    generated_text = (result.text or "").strip()
    canonical_payload = tool_result.canonical_payload if tool_result is not None else {}
    output_decision = check_output_safety(generated_text)
    numeric_result = validate_numeric_claims(generated_text, canonical_payload)
    if not generated_text or output_decision.blocked or not numeric_result.valid:
        return AssistantResponse(
            message=_UNSAFE_OUTPUT_FALLBACK_MESSAGE,
            execution_class=generated_execution_class,
            trace=AssistantTraceMeta(tools_invoked=tools_invoked, model_used=model_id),
        )

    return AssistantResponse(
        message=generated_text,
        execution_class=generated_execution_class,
        trace=AssistantTraceMeta(tools_invoked=tools_invoked, model_used=model_id),
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
        # (g) MODEL ROUTER: no deterministic tool could answer this — see
        # module docstring point (g) and _generate_model_response. Every
        # internal failure mode of that function degrades back to exactly
        # this honest response/execution_class, so this is still never a
        # fabricated answer, per (d).
        return await _generate_model_response(
            request,
            laya,
            intent_decision,
            tool_result=None,
            fallback_response_text=response_text,
            fallback_execution_class=execution_class,
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
