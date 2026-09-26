"""The ONLY permitted bridge into DualBeat's simulation code.

Reuses the existing, tested deterministic functions from
``python.hearttwin.tools.cardiac_state`` — CareGuard does not reimplement stroke
volume, ejection fraction, cardiac output, or MAP. Inputs are deep-copied; the
baseline is preserved and returned unchanged alongside each bounded scenario.
"""

from __future__ import annotations

import copy
from typing import Any

# Existing DualBeat functions — imported, never reimplemented.
from python.hearttwin.tools.cardiac_state import (
    compute_afterload_index,
    compute_cardiac_output,
    compute_ejection_fraction,
    compute_map,
    compute_stroke_volume,
)
from python.hearttwin.careguard.constants import SIMULATION_LABEL
from python.hearttwin.careguard.simulation import parameter_mapping, scenario_validator

REUSED_FUNCTIONS = [
    "python.hearttwin.tools.cardiac_state.compute_stroke_volume",
    "python.hearttwin.tools.cardiac_state.compute_ejection_fraction",
    "python.hearttwin.tools.cardiac_state.compute_cardiac_output",
    "python.hearttwin.tools.cardiac_state.compute_map",
    "python.hearttwin.tools.cardiac_state.compute_afterload_index",
]


def _metrics(inputs: dict[str, Any]) -> dict[str, float]:
    edv = float(inputs["edv_ml"])
    esv = float(inputs["esv_ml"])
    hr = float(inputs["heart_rate_bpm"])
    sbp = float(inputs["systolic_bp_mmhg"])
    dbp = float(inputs["diastolic_bp_mmhg"])
    sv = compute_stroke_volume(edv, esv)
    ef = compute_ejection_fraction(edv, esv)
    co = compute_cardiac_output(hr, sv)
    mp = compute_map(sbp, dbp)
    return {
        "stroke_volume_ml": round(sv, 2),
        "ejection_fraction_pct": round(ef, 2),
        "cardiac_output_l_min": round(co, 2),
        "mean_arterial_pressure_mmhg": round(mp, 2),
        "afterload_index": round(compute_afterload_index(mp, co), 3),
    }


def run_scenarios(baseline_inputs: dict[str, Any], levers: list[str]) -> dict[str, Any]:
    """Return baseline metrics + one bounded scenario per supported lever.

    Never mutates ``baseline_inputs``. Unsupported levers are rejected, not mapped.
    """
    inputs = copy.deepcopy(baseline_inputs)
    ok, reasons = scenario_validator.validate_baseline(inputs)
    if not ok:
        return {
            "ok": False,
            "reasons": reasons,
            "label": SIMULATION_LABEL,
            "reused_functions": [],
            "note": "DualBeat state incomplete — simulation comparison not run.",
        }

    baseline = _metrics(inputs)
    scenarios: list[dict[str, Any]] = []
    rejected: list[str] = []

    for lever in levers:
        if not parameter_mapping.is_supported(lever):
            rejected.append(lever)
            continue
        field, frac = parameter_mapping.resolve(lever)
        shifted = copy.deepcopy(inputs)
        if field == "map_mmhg":
            # afterload reduction → lower BP within bounds (both components).
            shifted["systolic_bp_mmhg"] = parameter_mapping.bounded_apply(inputs["systolic_bp_mmhg"], frac, lo=90, hi=200)
            shifted["diastolic_bp_mmhg"] = parameter_mapping.bounded_apply(inputs["diastolic_bp_mmhg"], frac, lo=50, hi=120)
        elif field == "esv_ml":
            shifted["esv_ml"] = parameter_mapping.bounded_apply(inputs["esv_ml"], frac, lo=10, hi=float(inputs["edv_ml"]) - 5)
        elif field == "heart_rate_bpm":
            shifted["heart_rate_bpm"] = parameter_mapping.bounded_apply(inputs["heart_rate_bpm"], frac, lo=45, hi=120)

        metrics = _metrics(shifted)
        deltas = {k: round(metrics[k] - baseline[k], 2) for k in baseline}
        scenarios.append({
            "lever": lever,
            "parameter": parameter_mapping.describe(lever),
            "metrics": metrics,
            "directional_delta_vs_baseline": deltas,
            "uncertainty": "Directional only; bounded per-scenario shift, not an outcome prediction.",
        })

    return {
        "ok": True,
        "label": SIMULATION_LABEL,
        "reused_functions": REUSED_FUNCTIONS,
        "baseline_preserved": baseline,
        "baseline_inputs_unchanged": inputs == baseline_inputs,
        "scenarios": scenarios,
        "rejected_levers": rejected,
    }
