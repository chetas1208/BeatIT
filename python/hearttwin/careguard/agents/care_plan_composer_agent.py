"""Agent 6 — Candidate Care-Plan Composer.

Generates 2–3 evidence-linked candidate review options (never one unquestioned
answer). Uses only verified guideline + drug-label evidence. Lists reasons for/
against, missing information, contraindications, sourced monitoring. Never a dose,
never an order; every candidate is clinician-review-required.
"""

from __future__ import annotations

from python.hearttwin.careguard.agents.base import StageTimer, make_stage_result
from python.hearttwin.careguard.constants import STAGE_CANDIDATE_COMPOSITION
from python.hearttwin.careguard.schemas import (
    CandidateCarePlan,
    CareGuardContext,
    CareGuardStageResult,
    EvidenceCitation,
    MedicationConflict,
)


def _cites(ctx: CareGuardContext) -> list[EvidenceCitation]:
    return [EvidenceCitation.model_validate(c) for c in (ctx.prior_stage_outputs.get("citations") or [])]


def _conflicts(ctx: CareGuardContext) -> list[MedicationConflict]:
    return [MedicationConflict.model_validate(c) for c in (ctx.prior_stage_outputs.get("conflicts") or [])]


def _cross_organ(ctx: CareGuardContext) -> dict[str, list[str]]:
    matrix = ctx.prior_stage_outputs.get("cross_organ_matrix") or {}
    out: dict[str, list[str]] = {}
    for cell in matrix.get("cells", []):
        notes = list(cell.get("factors", [])) + list(cell.get("missing_evidence", []))
        if notes:
            out[cell["domain"]] = notes
    return out


async def run(ctx: CareGuardContext) -> CareGuardStageResult:
    timer = StageTimer()
    cites = _cites(ctx)
    conflicts = _conflicts(ctx)
    cross = _cross_organ(ctx)
    missing = sorted({m for c in conflicts for m in c.missing_information} | set(ctx.missing_resources))
    monitoring_conflicts = [c for c in conflicts if c.conflict_type == "renal_potassium_risk"]

    monitoring = []
    for c in monitoring_conflicts:
        for cit in c.evidence_citations:
            monitoring.append({"parameter": "serum potassium and renal function",
                               "rationale": "label + guideline describe monitoring with reduced renal function",
                               "evidence_source_id": cit.source_id})
            break

    candidates: list[CandidateCarePlan] = []

    # Candidate A — continue guideline-concordant therapy with intensified monitoring.
    if cites:
        candidates.append(CandidateCarePlan(
            candidate_id="candidate-continue-monitor",
            title="Continue guideline-concordant therapy with intensified monitoring",
            description="Maintain the recorded heart-failure regimen while adding the monitoring the "
                        "guideline and drug labels describe for reduced renal function. For clinician review only.",
            guideline_basis=cites,
            matching_patient_fact_ids=ctx.prior_stage_outputs.get("matching_fact_ids", []),
            unmatched_or_unknown_criteria=["serum potassium not available to confirm safe MRA continuation"] if any(
                "potassium" in m.lower() for m in missing) else [],
            contraindications=monitoring_conflicts,
            drug_interactions=[],
            cross_organ_considerations=cross,
            missing_information=missing,
            monitoring_considerations=monitoring,
            follow_up_window=None,
            reasons_for=["Consistent with guideline-directed medical therapy for HFrEF",
                         "Preserves current regimen while closing the monitoring gap"],
            reasons_against=["Reduced eGFR with no recorded potassium raises hyperkalemia risk per labeling"],
            abstention_conditions=["Abstain from continuing potassium-affecting therapy unchanged until serum potassium is known"],
            confidence=0.6,
        ))

    # Candidate B — obtain missing evidence first.
    candidates.append(CandidateCarePlan(
        candidate_id="candidate-obtain-evidence",
        title="Obtain missing labs before any medication change",
        description="Prioritize obtaining the missing evidence (serum potassium, renal panel) that the "
                    "guideline and labels require before adjusting potassium-affecting therapy. Clinician review only.",
        guideline_basis=cites,
        matching_patient_fact_ids=[],
        unmatched_or_unknown_criteria=list(missing),
        contraindications=[],
        drug_interactions=[],
        cross_organ_considerations=cross,
        missing_information=missing,
        monitoring_considerations=monitoring,
        follow_up_window=None,
        reasons_for=["Directly closes the safety-critical evidence gap",
                     "Aligns with label guidance to check potassium/renal function"],
        reasons_against=["Defers therapy optimization until results are available"],
        abstention_conditions=["No medication change recommended until labs return"],
        confidence=0.7,
    ))

    # Candidate C — cautionary escalation option (flagged, not recommended).
    if monitoring_conflicts:
        candidates.append(CandidateCarePlan(
            candidate_id="candidate-escalate-cautionary",
            title="Escalate MRA therapy — CAUTION / not supported without potassium",
            description="An escalation option shown ONLY to make the risk explicit: labeling describes "
                        "hyperkalemia risk that rises with reduced renal function, and potassium is unknown. "
                        "Flagged cautionary for clinician review; no dose is provided.",
            guideline_basis=cites,
            contraindications=monitoring_conflicts,
            cross_organ_considerations=cross,
            missing_information=missing,
            monitoring_considerations=monitoring,
            follow_up_window=None,
            reasons_for=["Further GDMT intensification can be guideline-concordant when safe"],
            reasons_against=["Reduced eGFR + unknown potassium — labeling describes elevated hyperkalemia risk",
                             "Cannot be assessed safely without a potassium result"],
            abstention_conditions=["Do not escalate potassium-affecting therapy while potassium is unknown"],
            confidence=0.3,
        ))

    status = "completed" if len(candidates) >= 2 else "warning"
    return make_stage_result(
        ctx=ctx, stage_id=STAGE_CANDIDATE_COMPOSITION, timer=timer, status=status,
        structured_output={"candidates": [c.model_dump() for c in candidates],
                           "candidate_count": len(candidates)},
        source_ids=[cit.source_id for cit in cites],
        missing_information=missing,
        warnings=["fewer than 2 candidates"] if len(candidates) < 2 else [],
        confidence=0.7,
    )
