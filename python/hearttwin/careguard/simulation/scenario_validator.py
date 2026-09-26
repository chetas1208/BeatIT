"""Validate that a scenario's baseline inputs are complete and in physiologic
bounds before touching the DualBeat functions. Fails safe (returns reasons)."""

from __future__ import annotations

from typing import Any

BOUNDS = {
    "edv_ml": (60.0, 300.0),
    "esv_ml": (10.0, 250.0),
    "heart_rate_bpm": (30.0, 200.0),
    "systolic_bp_mmhg": (70.0, 250.0),
    "diastolic_bp_mmhg": (30.0, 150.0),
}


def validate_baseline(inputs: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for field, (lo, hi) in BOUNDS.items():
        val = inputs.get(field)
        if val is None:
            reasons.append(f"missing {field}")
            continue
        if not (lo <= float(val) <= hi):
            reasons.append(f"{field}={val} out of bounds [{lo},{hi}]")
    if inputs.get("esv_ml") is not None and inputs.get("edv_ml") is not None:
        if float(inputs["esv_ml"]) >= float(inputs["edv_ml"]):
            reasons.append("ESV must be < EDV")
    if inputs.get("diastolic_bp_mmhg") is not None and inputs.get("systolic_bp_mmhg") is not None:
        if float(inputs["diastolic_bp_mmhg"]) >= float(inputs["systolic_bp_mmhg"]):
            reasons.append("diastolic must be < systolic")
    return (not reasons), reasons
