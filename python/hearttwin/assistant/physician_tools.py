"""Wave 3 physician-tooling additions to the ONE canonical tool registry.

GLOBAL_ARCHITECTURE.md ("SINGLE TOOL REGISTRY") forbids a second, competing
registry (`physician_tools_v2`, `chat_tools`, ...). This module is NOT a
second registry: it imports `Tool`/`ToolRegistry`/`get_tool_registry`/
`ToolExecutionError` from `python.hearttwin.assistant.tool_registry` (Wave 2,
Agent 9) unmodified, and only adds new `Tool` instances to whatever
`ToolRegistry` it is given. `tool_registry.py` itself is not edited by this
file, per this wave's file-ownership constraint (Agent 11 is concurrently
touching orchestration code in the same wave).

Every handler below wraps a function or field that already exists and is
already load-bearing elsewhere in the backend — same discipline as Wave 2's
`tool_registry.py` docstring: no new physiology, uncertainty, or evidence
logic is added here. See `docs/assistant/wave3/physician-tooling.md` for the
exact file:line citation behind each tool and for the Part-A re-investigation
notes (what was found real vs. still frontend-only).

Registration is deliberately NOT performed at import time. `tool_registry.py`
lazily builds its singleton the first time `get_tool_registry()` is called;
this file follows the same discipline via `register_physician_tools()`,
which callers invoke explicitly on whichever `ToolRegistry` they intend to
wire up (production singleton or a fresh instance in a test). Auto-registering
into the process-wide singleton merely by importing this module would corrupt
Wave 2's own `test_tool_registry.py::test_default_registry_has_expected_tools_and_categories`,
which asserts an *exact* set of registered tool names on that singleton —
pytest imports every test module during collection, so an import-time side
effect in this file would leak into that test the moment both test files
exist in the same test session, regardless of run order. Explicit, caller-
invoked registration avoids that entirely and mirrors how Wave 2 left
`router.py` built but not mounted into `api.py` (WAVE_2_HANDOFF.md).
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from python.hearttwin.assistant.tool_registry import (
    Tool,
    ToolExecutionError,
    ToolRegistry,
    get_tool_registry,
)
from python.hearttwin.schemas import CaseRecord
from python.hearttwin.tools.storage import get_case

# ---------------------------------------------------------------------------
# Concrete tool handlers
#
# Same discipline as tool_registry.py: thin, read-only wrappers over already-
# persisted/computed data. No handler recomputes physiology, evidence, or
# provenance, or invents a fallback when data is missing — it raises
# ToolExecutionError instead (AGENTS.md §1).
# ---------------------------------------------------------------------------


async def _load_case(case_id: str) -> CaseRecord:
    case_data = await get_case(case_id)
    if not case_data:
        raise ToolExecutionError(f"case {case_id!r} not found")
    return CaseRecord(**case_data)


async def _handle_get_raw_provenance_ledger(*, case_id: str) -> dict[str, Any]:
    """Wraps `CardiacTwinState.source_map` (schemas.py:260), a
    `list[SourceMapEntry]` (schemas.py:232-240) attached to every case's
    simulated state.

    Part A re-investigation finding: this ledger is real, backend-native, and
    already consumed elsewhere in Python (`orchestrator.py:585`,
    `tools/scoring.py:161,182,240,297`, `tools/cardiac_findings.py:98-114`) —
    it is not frontend-only. What IS frontend-only, and what this tool does
    NOT attempt to fake, is binding each `source_map` entry to a UI component
    via `physiologyBindings` (`web/lib/heart/evidence/index.ts`) — that
    mapping table has no Python-side equivalent (confirmed by Wave 2 and
    re-confirmed here). This tool returns the ledger exactly as it exists on
    the backend: flat, keyed by `field` name, not grouped by anatomical
    component. Physicians asking "what evidence supports this component"
    still need the frontend's component report; physicians asking "show me
    the raw provenance for this case's values" get a real, honest answer here.
    """
    case = await _load_case(case_id)
    if case.state is None:
        raise ToolExecutionError(
            f"case {case_id!r} has no simulated state yet — call /operate before requesting provenance"
        )
    source_map = case.state.model_dump(mode="json")["source_map"]
    return {
        "case_id": case_id,
        "provenance_ledger": source_map,
        "scope": "raw",
        "note": (
            "This is the flat, field-keyed CardiacTwinState.source_map ledger, "
            "not a per-anatomical-component evidence view. Component-to-field "
            "binding (physiologyBindings) exists only in the frontend "
            "(web/lib/heart/evidence/index.ts) and has no backend equivalent."
        ),
    }


async def _handle_get_findings_by_region(*, case_id: str, region: str) -> dict[str, Any]:
    """Filters the real `get_cardiac_findings` tool's own output by its
    existing `region`/`territory` fields (`tools/cardiac_findings.py:151-264`,
    every finding dict already carries `region` and `territory`) — a slice of
    already-computed data, not a new component-binding layer.

    Calls the registered `get_cardiac_findings` tool directly (rather than
    re-importing `derive_findings`) so this handler can never drift from what
    that tool actually returns.

    Part A re-investigation finding: `derive_findings()` was fully re-read
    (`tools/cardiac_findings.py:129-272`). Wave 2's `get_cardiac_findings`
    already returns the *entire* dict `derive_findings()` produces (`findings`,
    `imaging_source`, `segment_model`, `disclaimer`, `model`) — nothing was
    left unexposed. What this tool adds is a narrower *view* over that same,
    already-complete data: physicians asking "what did the simulation find on
    the anteroseptal wall" currently have to read every finding themselves;
    this filters by the `region`/`territory` string each finding already
    carries. This is explicitly NOT the frontend's `getComponentEvidence()`
    (`web/lib/heart/evidence/index.ts:99-105`), which binds `source_map`
    fields to 3D-model components via `physiologyBindings` — no such binding
    table exists in Python, and none is invented here.
    """
    registry = get_tool_registry()
    result = await registry.execute("get_cardiac_findings", case_id=case_id)
    findings = result.canonical_payload["cardiac_findings"]["findings"]
    needle = region.strip().lower()
    matched = [
        finding
        for finding in findings
        if needle in str(finding.get("region") or "").lower()
        or needle == str(finding.get("territory") or "").lower()
    ]
    return {
        "case_id": case_id,
        "region_query": region,
        "matched_findings": matched,
        "match_count": len(matched),
        "segment_model": result.canonical_payload["cardiac_findings"]["segment_model"],
        "disclaimer": result.canonical_payload["cardiac_findings"]["disclaimer"],
    }


async def _handle_get_pv_loop(*, case_id: str) -> dict[str, Any]:
    """Wraps the baseline pressure-volume loop already computed by
    `generate_pressure_volume_loop` (`tools/hemodynamics.py:190`) and cached
    onto `CaseRecord.simulation_result["pv_loop"]` by `run_hemodynamics_agent`
    (`agents/hemodynamics_agent.py:672-686`) during `run_operation_pipeline`
    (`orchestrator.py:134-198`, sets `case.simulation_result` at line 198).

    Unlike `get_cardiac_findings` (which had to re-derive because
    `copilot.py`'s `operate` action skipped `derive_findings`), both real
    entry points to `/operate` — `api.py:1068` and `copilot.py:258`
    (`operate()`) — call the same `run_operation_pipeline`, so
    `simulation_result["pv_loop"]` is reliably populated by either path. This
    tool reads the cached value rather than recomputing it, the same pattern
    Wave 2 used for `get_ensemble`/`get_ensemble_distributions` reading a
    persisted store instead of recomputing.

    Part A re-investigation finding: `get_pv_loop` is explicitly named as a
    PHYSIOLOGY-category tool in GLOBAL_ARCHITECTURE.md's registry sketch but
    was never registered in Wave 2 — this is a real gap, not aspirational.
    This tool returns only the deterministic BASELINE loop from the most
    recent `/operate` run. The *scenario*-rescaled PV loop
    (`web/lib/twin/scenario/pv.ts:scenarioPvLoop()`) that PHYSICIAN_WORKFLOWS.md
    asked about remains frontend-only — re-confirmed here, no Python entry
    point exists for it (no scenario/counterfactual state is ever persisted
    server-side).
    """
    case = await _load_case(case_id)
    if not case.simulation_result:
        raise ToolExecutionError(
            f"case {case_id!r} has no simulation result yet — call /operate before requesting the PV loop"
        )
    pv_loop = case.simulation_result.get("pv_loop")
    if not pv_loop:
        raise ToolExecutionError(f"case {case_id!r}'s simulation result has no pv_loop payload")
    return {
        "case_id": case_id,
        "pv_loop": pv_loop,
        "note": (
            "Baseline deterministic PV loop from the most recent /operate run only. "
            "Scenario/counterfactual PV-loop rescaling is frontend-only "
            "(web/lib/twin/scenario/pv.ts) and has no backend entry point."
        ),
    }


async def _handle_get_ensemble_summary(*, ensemble_id: str) -> dict[str, Any]:
    """Composite tool: calls the three real, already-registered Wave 2
    ensemble tools (`get_ensemble`, `get_ensemble_distributions`,
    `get_ensemble_assumptions` — `tool_registry.py:240-296`) through the
    registry's own `execute()` and combines their real outputs. No ensemble
    logic is reimplemented — this only saves a physician-facing caller from
    making three separate tool calls to answer "summarize the plausible-twin
    ensemble."
    """
    registry = get_tool_registry()
    ensemble_result, distributions_result, assumptions_result = await asyncio.gather(
        registry.execute("get_ensemble", ensemble_id=ensemble_id),
        registry.execute("get_ensemble_distributions", ensemble_id=ensemble_id),
        registry.execute("get_ensemble_assumptions", ensemble_id=ensemble_id),
    )
    return {
        "ensemble_id": ensemble_id,
        "ensemble": ensemble_result.canonical_payload,
        "distributions": distributions_result.canonical_payload,
        "assumptions": assumptions_result.canonical_payload,
    }


# ---------------------------------------------------------------------------
# Tool definitions (not registered automatically — see module docstring)
# ---------------------------------------------------------------------------

_PHYSICIAN_TOOLS: tuple[Tool, ...] = (
    Tool(
        name="get_raw_provenance_ledger",
        description=(
            "Return the raw, flat, field-keyed provenance ledger "
            "(CardiacTwinState.source_map) for a case's most recent simulated "
            "state: for every field, its value, unit, source kind, "
            "confidence, method, and evidence. This is NOT bound to "
            "anatomical UI components — that binding exists only in the "
            "frontend."
        ),
        safety_level="T0",
        category="EVIDENCE",
        input_schema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "BeatIT case identifier."},
            },
            "required": ["case_id"],
        },
        handler=_handle_get_raw_provenance_ledger,
    ),
    Tool(
        name="get_findings_by_region",
        description=(
            "Return the subset of a case's cardiac findings (from "
            "get_cardiac_findings) whose region or coronary territory "
            "matches a query string, e.g. 'anteroseptal' or 'LAD'. A narrow "
            "view over already-computed findings, not a new evidence model."
        ),
        safety_level="T0",
        category="PHYSIOLOGY",
        input_schema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "BeatIT case identifier."},
                "region": {
                    "type": "string",
                    "description": "Region or territory substring to match, e.g. 'anteroseptal', 'apex', 'LAD'.",
                },
            },
            "required": ["case_id", "region"],
        },
        handler=_handle_get_findings_by_region,
    ),
    Tool(
        name="get_pv_loop",
        description=(
            "Return the deterministic baseline pressure-volume loop "
            "(volumes, pressures, loop area, stroke work, EF) from a case's "
            "most recent /operate simulation run. Baseline only — does not "
            "include scenario/counterfactual rescaling."
        ),
        safety_level="T0",
        category="PHYSIOLOGY",
        input_schema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "BeatIT case identifier."},
            },
            "required": ["case_id"],
        },
        handler=_handle_get_pv_loop,
    ),
    Tool(
        name="get_ensemble_summary",
        description=(
            "Return a previously computed plausible-twin ensemble's samples, "
            "metric distributions, and modeling assumptions together in one "
            "call, combining the real get_ensemble / get_ensemble_distributions "
            "/ get_ensemble_assumptions tool outputs."
        ),
        safety_level="T0",
        category="UNCERTAINTY",
        input_schema={
            "type": "object",
            "properties": {
                "ensemble_id": {"type": "string", "description": "Ensemble identifier returned by POST /api/v1/twin/ensemble."},
            },
            "required": ["ensemble_id"],
        },
        handler=_handle_get_ensemble_summary,
    ),
)


def register_physician_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    """Register Wave 3's physician tools onto `registry` (default: the real
    process-wide singleton from `get_tool_registry()`).

    Idempotent: skips any tool name already present, so calling this more
    than once (e.g. from multiple integration entry points) never raises
    `ToolRegistry.register`'s duplicate-name `ValueError`. Not called at
    import time — see module docstring for why.
    """
    target = registry if registry is not None else get_tool_registry()
    for tool in _PHYSICIAN_TOOLS:
        if target.get(tool.name) is None:
            target.register(tool)
    return target
