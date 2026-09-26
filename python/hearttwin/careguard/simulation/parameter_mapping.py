"""Map candidate review options to SUPPORTED, bounded simulation parameters.

Only a small allow-list of physiologic directions is supported; anything else is
rejected (never silently mapped). Shifts are bounded to a safe per-scenario step.
"""

from __future__ import annotations

from typing import Any

# Supported directional levers → (field, fractional bound).
SUPPORTED_LEVERS = {
    "afterload_reduction": ("map_mmhg", -0.12),
    "preload_optimization": ("esv_ml", -0.10),
    "rate_control": ("heart_rate_bpm", -0.10),
    "baseline": (None, 0.0),
}


def is_supported(lever: str) -> bool:
    return lever in SUPPORTED_LEVERS


def resolve(lever: str) -> tuple[str | None, float]:
    if lever not in SUPPORTED_LEVERS:
        raise ValueError(f"unsupported simulation lever: {lever!r}")
    return SUPPORTED_LEVERS[lever]


def bounded_apply(value: float, fraction: float, *, lo: float, hi: float) -> float:
    shifted = value * (1.0 + fraction)
    return max(lo, min(hi, shifted))


def describe(lever: str) -> dict[str, Any]:
    field, frac = SUPPORTED_LEVERS.get(lever, (None, 0.0))
    return {"lever": lever, "field": field, "bounded_fraction": frac}
