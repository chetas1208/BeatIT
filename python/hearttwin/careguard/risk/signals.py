"""Extract deterministic clinical signals from a PatientContext.

Pure reads of recorded facts — no inference of unrecorded conditions.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.schemas import PatientContext


def _find_obs(ctx: PatientContext, *codes: str) -> Any:
    for f in ctx.observations:
        if f.code in codes:
            return f
    return None


def extract_signals(ctx: PatientContext) -> dict[str, Any]:
    egfr = _find_obs(ctx, "48642-3")
    creat = _find_obs(ctx, "2160-0")
    ef = _find_obs(ctx, "10230-1")
    potassium = _find_obs(ctx, "2823-3", "6298-4")

    egfr_val = egfr.value if egfr and isinstance(egfr.value, (int, float)) else None
    ef_val = ef.value if ef and isinstance(ef.value, (int, float)) else None

    conditions = " ".join(
        str(f.display or "").lower()
        for f in (ctx.active_cardiac_problem + ctx.active_non_cardiac_conditions + ctx.historical_cardiac_problems)
    )

    return {
        "egfr_value": egfr_val,
        "egfr_fact_id": egfr.fact_id if egfr else None,
        "creatinine_fact_id": creat.fact_id if creat else None,
        "ef_value": ef_val,
        "ef_fact_id": ef.fact_id if ef else None,
        "reduced_egfr": bool(egfr_val is not None and egfr_val < 60),
        "severe_egfr": bool(egfr_val is not None and egfr_val < 30),
        "missing_potassium": potassium is None,
        "ckd_recorded": ("kidney" in conditions or "ckd" in conditions),
        "copd_recorded": ("copd" in conditions or "obstructive pulmonary" in conditions),
        "asthma_recorded": "asthma" in conditions,
        "diabetes_recorded": "diabet" in conditions,
        "liver_recorded": ("hepati" in conditions or "cirrhos" in conditions or "liver" in conditions),
        "pregnancy_recorded": "pregnan" in conditions,
        "frailty_recorded": "frail" in conditions,
        "allergen_terms": [str(a.display or "").lower().split()[0] for a in ctx.allergies if a.display],
        "allergy_fact_ids": [a.fact_id for a in ctx.allergies],
        "medication_fact_ids": [m.fact_id for m in ctx.medications],
        "missing_critical_evidence": list(ctx.missing_critical_evidence),
    }
