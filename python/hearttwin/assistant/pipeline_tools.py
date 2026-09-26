"""Deterministic pipeline stages on the ONE canonical assistant registry."""

from __future__ import annotations

from typing import Any, Optional

from python.hearttwin.assistant.schemas import ExecutionClass
from python.hearttwin.assistant.tool_registry import Tool, ToolExecutionError, ToolRegistry, get_tool_registry


async def _handle_run_cardiac_operate(case_id: str) -> dict[str, Any]:
    from python.hearttwin import copilot

    try:
        return await copilot.operate(case_id)
    except ValueError as exc:
        raise ToolExecutionError(str(exc)) from exc


async def _handle_run_recovery_simulation(case_id: str) -> dict[str, Any]:
    from python.hearttwin import copilot

    try:
        return await copilot.simulate_recovery(case_id)
    except ValueError as exc:
        raise ToolExecutionError(str(exc)) from exc


def register_pipeline_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    target = registry or get_tool_registry()
    target.register(
        Tool(
            name="run_cardiac_operate",
            description=(
                "Run the deterministic cardiac operate stage for a case that already "
                "has validated vitals (same logic as REST operate)."
            ),
            safety_level="T1",
            category="EXPERIMENT",
            input_schema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "DualBeat case identifier."},
                },
                "required": ["case_id"],
            },
            handler=_handle_run_cardiac_operate,
            execution_class=ExecutionClass.SIMULATION,
        )
    )
    target.register(
        Tool(
            name="run_recovery_simulation",
            description=(
                "Run bounded recovery scenario simulation after operate "
                "(same logic as REST simulate_recovery)."
            ),
            safety_level="T1",
            category="EXPERIMENT",
            input_schema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "DualBeat case identifier."},
                },
                "required": ["case_id"],
            },
            handler=_handle_run_recovery_simulation,
            execution_class=ExecutionClass.DETERMINISTIC_COMPUTATION,
        )
    )
    return target
