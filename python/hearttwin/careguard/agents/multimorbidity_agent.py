"""Agent 3 — Clinical Problem & Multimorbidity.

Builds the cross-organ consideration matrix, separates recorded facts from gaps,
and lists the guideline domains that must be searched. Never diagnoses.
"""

from __future__ import annotations

from python.hearttwin.careguard.agents.base import StageTimer, make_stage_result
from python.hearttwin.careguard.constants import STAGE_MULTIMORBIDITY
from python.hearttwin.careguard.risk.cross_organ_matrix import build_matrix
from python.hearttwin.careguard.schemas import CareGuardContext, CareGuardStageResult, PatientContext


def _guideline_domains(matrix) -> list[str]:
    domains = []
    for cell in matrix.cells:
        if cell.status in ("caution", "high") and cell.domain not in ("missing_evidence", "drug_interaction"):
            domains.append(cell.domain)
    return domains


async def run(ctx: CareGuardContext) -> CareGuardStageResult:
    timer = StageTimer()
    pc_dict = ctx.prior_stage_outputs.get("patient_context")
    patient_context = PatientContext.model_validate(pc_dict) if pc_dict else PatientContext(case_id=ctx.case_id)

    scope = ctx.clinical_question or "Cardiac care-plan evidence review with multimorbidity considerations"
    matrix = build_matrix(patient_context, review_scope=scope)

    missing_cells = [c for c in matrix.cells if c.missing_evidence]
    missing = sorted({m for c in missing_cells for m in c.missing_evidence})
    domains = _guideline_domains(matrix)

    return make_stage_result(
        ctx=ctx, stage_id=STAGE_MULTIMORBIDITY, timer=timer,
        status="warning" if missing else "completed",
        structured_output={
            "review_scope": scope,
            "cross_organ_matrix": matrix.model_dump(),
            "risk_domains_requiring_evidence": domains,
            "recorded_multimorbidity_factors": [
                {"domain": c.domain, "factors": c.factors} for c in matrix.cells if c.factors
            ],
        },
        source_ids=[i for c in matrix.cells for i in c.patient_fact_ids],
        missing_information=missing,
        warnings=[f"cross-organ gaps: {', '.join(missing)}"] if missing else [],
        confidence=0.8,
    )
