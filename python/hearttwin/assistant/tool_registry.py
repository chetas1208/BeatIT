"""Canonical BeatIT assistant tool registry (Wave 2).

GLOBAL_ARCHITECTURE.md ("SINGLE TOOL REGISTRY") requires exactly ONE tool
layer for the whole assistant — no `physician_tools_v2`, `chat_tools`,
`laya_tools`, etc. This module is that registry.

Every tool registered here wraps a function that already exists and is
already load-bearing elsewhere in the backend (`python/hearttwin/tools/
cardiac_findings.py`, `python/hearttwin/ensemble.py`, `python/hearttwin/
storage/ensemble_store.py`) — this file adds no new physiology or
uncertainty logic, only a uniform, LLM-callable surface over what is already
real. See `docs/assistant/wave2/tool-registry.md` for the exact file:line
citation and signature verification behind each tool, and for the list of
`docs/assistant/PHYSICIAN_WORKFLOWS.md` candidates deliberately NOT
implemented here (most of that doc's candidate list is frontend-only
TypeScript under `web/lib/twin/` / `web/lib/heart/` with no Python entry
point to wrap).

Result shape reuses `python.hearttwin.assistant.schemas.ToolResult` (Agent 6,
Wave 2) rather than defining a second, competing result contract.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from python.hearttwin.assistant.schemas import ExecutionClass, ToolResult
from python.hearttwin.schemas import CaseRecord
from python.hearttwin.storage.ensemble_store import EnsembleStoreError, create_ensemble_store
from python.hearttwin.tools.cardiac_findings import derive_findings
from python.hearttwin.tools.storage import get_case

SafetyLevel = Literal["T0", "T1", "T2", "T3"]

# Categories from GLOBAL_ARCHITECTURE.md "SINGLE TOOL REGISTRY" verbatim.
# A tool registered under any other category is almost certainly a sign of a
# second, competing taxonomy forming — reject it rather than silently accept.
VALID_CATEGORIES = frozenset({
    "TWIN",
    "EVIDENCE",
    "PHYSIOLOGY",
    "EXPERIMENT",
    "COMPARE",
    "UNCERTAINTY",
    "REPORT",
})

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


class ToolNotFoundError(KeyError):
    """Raised by `ToolRegistry.execute`/`get` for an unregistered tool name."""

    def __init__(self, name: str, known_names: list[str]) -> None:
        self.name = name
        self.known_names = known_names
        super().__init__(
            f"unknown tool {name!r}; registered tools: {', '.join(sorted(known_names)) or '(none)'}"
        )


class ToolExecutionError(RuntimeError):
    """Raised when a registered tool's handler cannot fulfill a call.

    Distinct from ToolNotFoundError so callers (Laya / the model router) can
    tell "wrong name" apart from "right tool, bad/missing data" without
    parsing message strings.
    """


class Tool(BaseModel):
    """One entry in the canonical registry.

    `execution_class` is not in the Wave-2 task brief's minimal field list
    but is required to populate `ToolResult.execution_class` (schemas.py) on
    every call — see docs/assistant/wave2/tool-registry.md for why it was
    added rather than guessed at per-call.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    safety_level: SafetyLevel
    category: str
    input_schema: dict[str, Any]
    handler: ToolHandler
    execution_class: ExecutionClass = ExecutionClass.EVIDENCE_RETRIEVAL

    def _validate_category(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"tool {self.name!r}: category {self.category!r} is not one of "
                f"GLOBAL_ARCHITECTURE.md's registry categories: {sorted(VALID_CATEGORIES)}"
            )

    def model_post_init(self, __context: Any) -> None:  # noqa: D401 - pydantic hook
        self._validate_category()


class ToolRegistry:
    """The one BeatIT tool registry (GLOBAL_ARCHITECTURE.md "SINGLE TOOL REGISTRY").

    Deliberately minimal: registration, lookup, and execution. Laya/tool
    selection, the numeric-claim validator, and the safety guardrail layers
    are separate, later concerns (see GLOBAL_ARCHITECTURE.md "GUARDRAIL
    LAYERS") and are not reimplemented inside the registry itself.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> list[Tool]:
        tools = list(self._tools.values())
        if category is None:
            return tools
        return [tool for tool in tools if tool.category == category]

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            raise ToolNotFoundError(name, list(self._tools))
        payload = await tool.handler(**kwargs)
        return ToolResult(
            tool_name=tool.name,
            execution_class=tool.execution_class,
            canonical_payload=payload,
            safety_level=tool.safety_level,
        )


# ---------------------------------------------------------------------------
# Concrete tool handlers
#
# Each handler is a thin, read-only wrapper: fetch already-persisted data via
# the same functions the real API routes use, call the same real function on
# it, and shape the result. No handler recomputes physiology or invents a
# fallback value when data is missing — it raises ToolExecutionError instead,
# per AGENTS.md §1 ("the deterministic physics core is sacred").
# ---------------------------------------------------------------------------


async def _handle_get_cardiac_findings(*, case_id: str) -> dict[str, Any]:
    """Wraps `derive_findings` (tools/cardiac_findings.py:129), the same call
    `POST /api/v1/cases/{case_id}/operate` makes (api.py:973) — reproduced
    here instead of read from the cached `simulation_result` key so this tool
    also works for cases operated through `copilot.py`'s `operate` action,
    which does not call `derive_findings` itself (verified: no reference to
    cardiac_findings/derive_findings in copilot.py).
    """
    case_data = await get_case(case_id)
    if not case_data:
        raise ToolExecutionError(f"case {case_id!r} not found")
    case = CaseRecord(**case_data)
    if case.state is None:
        raise ToolExecutionError(
            f"case {case_id!r} has no simulated state yet — call /operate before requesting findings"
        )
    findings = derive_findings(case.state.model_dump(mode="json"), case.simulation_result)
    return {"case_id": case_id, "cardiac_findings": findings}


async def _load_ensemble(ensemble_id: str) -> dict[str, Any]:
    store = create_ensemble_store()
    try:
        result = await asyncio.to_thread(store.get, ensemble_id)
    except (EnsembleStoreError, OSError) as exc:
        raise ToolExecutionError("ensemble persistence is unavailable") from exc
    if result is None:
        raise ToolExecutionError(f"ensemble {ensemble_id!r} not found")
    return result


async def _handle_get_ensemble(*, ensemble_id: str) -> dict[str, Any]:
    """Wraps the same store lookup as `GET /api/v1/twin/ensemble/{id}` (api.py:171-179)."""
    return await _load_ensemble(ensemble_id)


async def _handle_get_ensemble_distributions(*, ensemble_id: str) -> dict[str, Any]:
    """Wraps the same store lookup + slice as
    `GET /api/v1/twin/ensemble/{id}/distributions` (api.py:182-195)."""
    result = await _load_ensemble(ensemble_id)
    return {
        "ensemble_id": ensemble_id,
        "distributions": result["distributions"],
        "provenance": result["provenance"],
        "safety_disclaimer": result["safety_disclaimer"],
    }


async def _handle_get_ensemble_assumptions(*, ensemble_id: str) -> dict[str, Any]:
    """Slices `EnsembleProvenance.assumptions` (ensemble.py:233,435) out of the
    same persisted ensemble record — the only structured "assumptions" data
    in the backend (see PHYSICIAN_WORKFLOWS.md "Existing Evidence/Provenance
    Model")."""
    result = await _load_ensemble(ensemble_id)
    provenance = result["provenance"]
    return {
        "ensemble_id": ensemble_id,
        "assumptions": provenance.get("assumptions", []),
        "origin_quality": provenance.get("origin_quality"),
        "safety_disclaimer": result["safety_disclaimer"],
    }


def _build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(Tool(
        name="get_cardiac_findings",
        description=(
            "Return the deterministic, AHA-17-segment-localized educational findings "
            "(region, coronary territory, severity, reference codes) for a case's most "
            "recent simulated cardiac state. Read-only; never a diagnosis."
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
        handler=_handle_get_cardiac_findings,
        execution_class=ExecutionClass.EVIDENCE_RETRIEVAL,
    ))

    registry.register(Tool(
        name="get_ensemble",
        description=(
            "Return a previously computed plausible-twin ensemble by id: every sample, "
            "its accept/reject status, and the four canonical output-metric distributions."
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
        handler=_handle_get_ensemble,
        execution_class=ExecutionClass.EVIDENCE_RETRIEVAL,
    ))

    registry.register(Tool(
        name="get_ensemble_distributions",
        description=(
            "Return only the metric distributions + lineage provenance for a previously "
            "computed ensemble, without the full per-sample list."
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
        handler=_handle_get_ensemble_distributions,
        execution_class=ExecutionClass.EVIDENCE_RETRIEVAL,
    ))

    registry.register(Tool(
        name="get_ensemble_assumptions",
        description=(
            "Return the explicit, human-readable modeling assumptions recorded for a "
            "previously computed ensemble (e.g. independence-sampling caveats) plus its "
            "origin data quality."
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
        handler=_handle_get_ensemble_assumptions,
        execution_class=ExecutionClass.EVIDENCE_RETRIEVAL,
    ))

    return registry


_REGISTRY: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Process-wide singleton, mirroring `models/registry.py:get_model_registry`."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_default_registry()
    return _REGISTRY
