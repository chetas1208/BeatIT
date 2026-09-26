"""Assemble the cross-organ risk matrix from recorded signals.

One RiskCell per domain (spec §10, Agent 3). 'unknown' when evidence is absent —
never a fabricated 'ok'. Missing evidence is a first-class cell.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.risk.signals import extract_signals
from python.hearttwin.careguard.schemas import CrossOrganMatrix, PatientContext, RiskCell


def _cardiac(s: dict[str, Any], ctx: PatientContext) -> RiskCell:
    ids = [f.fact_id for f in ctx.active_cardiac_problem]
    if not ctx.active_cardiac_problem:
        return RiskCell(domain="cardiac", status="unknown", note="No active cardiac problem recorded.")
    factors = [str(f.display) for f in ctx.active_cardiac_problem]
    status = "caution"
    if s["ef_value"] is not None and s["ef_value"] < 40:
        status = "high"
        factors.append(f"reduced ejection fraction {s['ef_value']}%")
    return RiskCell(domain="cardiac", status=status, factors=factors, patient_fact_ids=ids)


def _renal(s: dict[str, Any]) -> RiskCell:
    if s["egfr_value"] is None:
        return RiskCell(
            domain="renal", status="unknown",
            missing_evidence=["no eGFR recorded"],
            note="Renal function not quantified.",
        )
    status = "high" if s["severe_egfr"] else ("caution" if s["reduced_egfr"] else "ok")
    return RiskCell(
        domain="renal", status=status,
        factors=[f"eGFR {s['egfr_value']} mL/min/1.73m2"],
        patient_fact_ids=[i for i in [s["egfr_fact_id"], s["creatinine_fact_id"]] if i],
    )


def _hepatic(s: dict[str, Any]) -> RiskCell:
    if not s["liver_recorded"]:
        return RiskCell(domain="hepatic", status="unknown", missing_evidence=["no hepatic condition or LFTs recorded"])
    return RiskCell(domain="hepatic", status="caution", factors=["recorded hepatic condition"])


def _pulmonary(s: dict[str, Any]) -> RiskCell:
    if s["copd_recorded"] or s["asthma_recorded"]:
        f = ["COPD"] if s["copd_recorded"] else []
        if s["asthma_recorded"]:
            f.append("asthma")
        return RiskCell(domain="pulmonary", status="caution", factors=f,
                        note="Recorded airway disease — relevant to beta-blocker tolerance considerations.")
    return RiskCell(domain="pulmonary", status="unknown", missing_evidence=["no pulmonary condition recorded"])


def _metabolic(s: dict[str, Any]) -> RiskCell:
    if s["diabetes_recorded"]:
        return RiskCell(domain="metabolic", status="caution", factors=["diabetes recorded"])
    return RiskCell(domain="metabolic", status="unknown", missing_evidence=["no metabolic condition/HbA1c recorded"])


def _bleeding(s: dict[str, Any]) -> RiskCell:
    return RiskCell(domain="bleeding", status="unknown",
                    missing_evidence=["no anticoagulant/INR evidence recorded"])


def _allergy(s: dict[str, Any], ctx: PatientContext) -> RiskCell:
    if ctx.allergies:
        return RiskCell(domain="allergy", status="caution",
                        factors=[str(a.display) for a in ctx.allergies],
                        patient_fact_ids=s["allergy_fact_ids"])
    return RiskCell(domain="allergy", status="unknown", missing_evidence=["no allergy information recorded"])


def _pregnancy(s: dict[str, Any]) -> RiskCell:
    if s["pregnancy_recorded"]:
        return RiskCell(domain="pregnancy", status="high", factors=["pregnancy recorded"])
    return RiskCell(domain="pregnancy", status="not_applicable", note="Pregnancy status not recorded.")


def _frailty(s: dict[str, Any]) -> RiskCell:
    if s["frailty_recorded"]:
        return RiskCell(domain="frailty", status="caution", factors=["frailty recorded"])
    return RiskCell(domain="frailty", status="unknown", missing_evidence=["no frailty marker recorded"])


def _drug_interaction(s: dict[str, Any]) -> RiskCell:
    return RiskCell(domain="drug_interaction", status="unknown",
                    patient_fact_ids=s["medication_fact_ids"],
                    note="Populated by the medication-safety stage from official label evidence.")


def _missing_evidence(s: dict[str, Any]) -> RiskCell:
    miss = s["missing_critical_evidence"]
    return RiskCell(
        domain="missing_evidence",
        status="high" if miss else "ok",
        missing_evidence=miss,
        note="Critical evidence gaps that block safe comparison." if miss else "No critical gaps detected.",
    )


def build_matrix(ctx: PatientContext, *, review_scope: str = "") -> CrossOrganMatrix:
    s = extract_signals(ctx)
    cells = [
        _cardiac(s, ctx), _renal(s), _hepatic(s), _pulmonary(s), _metabolic(s),
        _bleeding(s), _allergy(s, ctx), _pregnancy(s), _frailty(s),
        _drug_interaction(s), _missing_evidence(s),
    ]
    return CrossOrganMatrix(case_id=ctx.case_id, cells=cells, review_scope=review_scope)
