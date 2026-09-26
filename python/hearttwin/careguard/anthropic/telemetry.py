"""Redacted model-call telemetry. Stores model + status + latency ONLY.

Never stores prompts, payloads, or model reasoning (spec §7 logging boundary).
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.feature_flags import log_raw_model_inputs, log_raw_model_outputs
from python.hearttwin.careguard.security import redact_structured

_CALLS: list[dict[str, Any]] = []
_MAX = 500


def record_call(*, stage_id: str, model: str, status: str, detail: dict | None = None) -> None:
    entry = {
        "stage_id": stage_id,
        "model": model,
        "status": status,
        "detail": redact_structured(detail or {}),
        "raw_inputs_logged": log_raw_model_inputs(),   # visibility into posture
        "raw_outputs_logged": log_raw_model_outputs(),
    }
    if len(_CALLS) >= _MAX:
        _CALLS.pop(0)
    _CALLS.append(entry)


def recent(limit: int = 50) -> list[dict]:
    return _CALLS[-limit:]


def reset() -> None:
    _CALLS.clear()
