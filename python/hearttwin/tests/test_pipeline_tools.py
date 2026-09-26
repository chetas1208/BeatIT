"""Pipeline stages on the unified tool registry."""

from __future__ import annotations

import pytest

from python.hearttwin import copilot
from python.hearttwin.assistant.tool_registry import get_tool_registry
from python.hearttwin.tests.test_pipeline_actions import GOLDEN_VITALS


@pytest.mark.asyncio
async def test_run_cardiac_operate_tool_matches_copilot_action() -> None:
    case = await copilot.create_case()
    case_id = case["case_id"]
    await copilot.extract(case_id, **GOLDEN_VITALS)

    registry = get_tool_registry()
    direct = await copilot.operate(case_id)
    via_tool = await registry.execute("run_cardiac_operate", case_id=case_id)

    assert via_tool.canonical_payload["ok"] is True
    assert via_tool.canonical_payload["summary"]["ef_pct"] == direct["summary"]["ef_pct"]
