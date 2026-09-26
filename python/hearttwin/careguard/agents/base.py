"""Shared helpers for CareGuard agents: timing + StageResult construction.

Timing uses ``time.monotonic`` (a duration, not a wall clock) so it stays
deterministic-safe and never needs ``Date.now``-style absolute time inside logic.
Timestamps are ISO strings for display only.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from python.hearttwin.careguard.constants import STAGE_AGENT
from python.hearttwin.careguard.schemas import CareGuardStageResult


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StageTimer:
    def __init__(self) -> None:
        self.started_at = now_iso()
        self._t0 = time.monotonic()

    def latency_ms(self) -> int:
        return int((time.monotonic() - self._t0) * 1000)


def make_stage_result(
    *,
    ctx,
    stage_id: str,
    timer: StageTimer,
    status: str,
    structured_output: dict[str, Any],
    model_used: str | None = None,
    source_ids: list[str] | None = None,
    tools_called: list[dict] | None = None,
    warnings: list[str] | None = None,
    missing_information: list[str] | None = None,
    safety_flags: list[str] | None = None,
    confidence: float = 0.0,
    audit_event_ids: list[str] | None = None,
) -> CareGuardStageResult:
    agent_id, agent_name = STAGE_AGENT.get(stage_id, ("careguard_agent", "CareGuard Agent"))
    return CareGuardStageResult(
        run_id=ctx.run_id,
        case_id=ctx.case_id,
        stage_id=stage_id,
        agent_id=agent_id,
        agent_name=agent_name,
        model_used=model_used,
        status=status,  # type: ignore[arg-type]
        started_at=timer.started_at,
        completed_at=now_iso(),
        latency_ms=timer.latency_ms(),
        source_ids=source_ids or [],
        tools_called=tools_called or [],
        structured_output=structured_output,
        warnings=warnings or [],
        missing_information=missing_information or [],
        safety_flags=safety_flags or [],
        confidence=confidence,
        audit_event_ids=audit_event_ids or [],
    )
