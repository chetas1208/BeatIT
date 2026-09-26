"""Detect and record model refusals (Fable may refuse with HTTP 200).

A refusal is NOT a successful empty answer. When detected, the caller retries on
the fallback model and, failing that, returns a safe abstention.
"""

from __future__ import annotations

from typing import Any

REFUSAL_STOP_REASONS = {"refusal"}


def is_refusal(response: Any) -> bool:
    stop = getattr(response, "stop_reason", None)
    if stop is None and isinstance(response, dict):
        stop = response.get("stop_reason")
    return stop in REFUSAL_STOP_REASONS


def refusal_metadata(response: Any, model: str) -> dict:
    """Redacted refusal record — model + stop_reason only, never content."""
    stop = getattr(response, "stop_reason", None)
    if stop is None and isinstance(response, dict):
        stop = response.get("stop_reason")
    return {"model": model, "stop_reason": stop, "handled": True, "content_stored": False}
