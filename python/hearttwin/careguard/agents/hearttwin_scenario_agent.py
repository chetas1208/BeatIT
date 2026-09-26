"""Agent 7 — DualBeat Scenario.

Uses the read-only DualBeat adapter to run bounded physiologic scenario
comparisons. Preserves the baseline, shows directional differences with
uncertainty, and never predicts clinical efficacy or patient outcome.
"""

from __future__ import annotations

from python.hearttwin.careguard.agents.base import StageTimer, make_stage_result
from python.hearttwin.careguard.constants import SIMULATION_LABEL, STAGE_HEARTTWIN_SCENARIOS
from python.hearttwin.careguard.schemas import CareGuardContext, CareGuardStageResult, PatientContext
from python.hearttwin.careguard.simulation import hearttwin_adapter

_EDV_HINTS = ("end diastolic volume", "end-diastolic")
_ESV_HINTS = ("end systolic volume", "end-systolic")


def _find(pc: PatientContext, codes=(), hints=()):
    for f in pc.observations:
        if f.code in codes:
            return f
        disp = str(f.display or "").lower()
        if hints and any(h in disp for h in hints):
            return f
    return None


def _baseline_inputs(pc: PatientContext) -> dict | None:
    edv = _find(pc, ("8823-1",), _EDV_HINTS)
    esv = _find(pc, ("8824-9",), _ESV_HINTS)
    hr = _find(pc, ("8867-4",))
    sbp = _find(pc, ("8480-6",))
    dbp = _find(pc, ("8462-4",))
    if not all(x and isinstance(x.value, (int, float)) for x in (edv, esv, hr, sbp, dbp)):
        return None
    return {
        "edv_ml": float(edv.value), "esv_ml": float(esv.value),
        "heart_rate_bpm": float(hr.value),
        "systolic_bp_mmhg": float(sbp.value), "diastolic_bp_mmhg": float(dbp.value),
    }


async def run(ctx: CareGuardContext) -> CareGuardStageResult:
    timer = StageTimer()
    pc_dict = ctx.prior_stage_outputs.get("patient_context")
    pc = PatientContext.model_validate(pc_dict) if pc_dict else PatientContext(case_id=ctx.case_id)

    inputs = _baseline_inputs(pc)
    if inputs is None:
        return make_stage_result(
            ctx=ctx, stage_id=STAGE_HEARTTWIN_SCENARIOS, timer=timer, status="warning",
            structured_output={
                "ran": False,
                "reason": "Incomplete DualBeat state (need EDV, ESV, HR, and BP) — comparison not run.",
                "label": SIMULATION_LABEL,
            },
            warnings=["DualBeat simulation skipped: incomplete volumetric state"],
            confidence=0.2,
        )

    result = hearttwin_adapter.run_scenarios(inputs, ["baseline", "afterload_reduction", "preload_optimization"])
    tools = [{"tool": "run_hearttwin_scenario", "reused_functions": result.get("reused_functions", [])}]

    return make_stage_result(
        ctx=ctx, stage_id=STAGE_HEARTTWIN_SCENARIOS, timer=timer,
        status="completed" if result.get("ok") else "warning",
        structured_output={
            "ran": bool(result.get("ok")),
            "simulation": result,
            "label": SIMULATION_LABEL,
            "baseline_inputs_unchanged": result.get("baseline_inputs_unchanged"),
        },
        tools_called=tools,
        warnings=["unsupported levers rejected: " + ", ".join(result.get("rejected_levers", []))]
        if result.get("rejected_levers") else [],
        confidence=0.7 if result.get("ok") else 0.3,
    )
