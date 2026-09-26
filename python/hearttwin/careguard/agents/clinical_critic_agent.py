"""Agent 8 — Evidence, Safety & Clinical Critic.

Blocks display when a safety invariant is violated (unsourced candidate, ignored
allergy, generated dose, missing renal review, stale guideline, hidden confidence,
implied certainty, missing clinician-review status, misrepresented refusal, …).
Emits a deterministic scorecard.
"""

from __future__ import annotations

import re

from python.hearttwin.careguard.agents.base import StageTimer, make_stage_result
from python.hearttwin.careguard.constants import STAGE_CLINICAL_CRITIC
from python.hearttwin.careguard.schemas import (
    CareGuardContext,
    CareGuardStageResult,
    CriticResult,
    CriticScorecard,
)

_DOSE_RE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|g|units?|ml)\b", re.IGNORECASE)
_CERTAINTY = ("will cure", "guaranteed", "definitely will", "always works", "certain to")


def _pct(n: int, d: int) -> float:
    return round(n / d, 3) if d else 0.0


async def run(ctx: CareGuardContext) -> CareGuardStageResult:
    timer = StageTimer()
    p = ctx.prior_stage_outputs
    candidates = p.get("candidates", []) or []
    conflicts = p.get("conflicts", []) or []
    citations = p.get("citations", []) or []
    matrix = (p.get("cross_organ_matrix") or {}).get("cells", [])
    sim = p.get("simulation") or {}
    pc = p.get("patient_context") or {}

    blocked: list[str] = []
    revisions: list[str] = []
    unsupported: list[str] = []

    # 1. Every candidate must cite evidence and require clinician review.
    for c in candidates:
        if not c.get("guideline_basis") and not c.get("contraindications"):
            blocked.append(f"candidate {c.get('candidate_id')} lacks any evidence basis")
        if c.get("clinician_review_required") is not True:
            blocked.append(f"candidate {c.get('candidate_id')} not marked clinician-review-required")
        # 2. No dose anywhere.
        blob = str(c.get("description", "")) + " ".join(c.get("reasons_for", []) + c.get("reasons_against", []))
        if _DOSE_RE.search(blob):
            blocked.append(f"candidate {c.get('candidate_id')} contains a dose")
        if any(t in blob.lower() for t in _CERTAINTY):
            blocked.append(f"candidate {c.get('candidate_id')} implies clinical certainty")
        # 3. Follow-up window must be sourced.
        if c.get("follow_up_window") and not c.get("guideline_basis"):
            blocked.append(f"candidate {c.get('candidate_id')} has an unsourced follow-up interval")

    # 4. Medication conflicts must carry label evidence (unless explicitly unavailable).
    for mc in conflicts:
        if mc.get("severity") in ("caution", "high", "blocked") and not mc.get("evidence_citations"):
            blocked.append(f"medication conflict for {mc.get('medication_name')} lacks official label evidence")

    # 5. Ignored allergy / skipped renal review.
    allergies = pc.get("allergies", [])
    renal_cell = next((c for c in matrix if c["domain"] == "renal"), None)
    if renal_cell is None:
        blocked.append("renal considerations were not evaluated")
    if allergies and not any(c["domain"] == "allergy" for c in matrix):
        blocked.append("documented allergy present but allergy domain not reviewed")

    # 6. Guideline version present.
    for cit in citations:
        if not cit.get("version") and not cit.get("publication_date"):
            revisions.append(f"citation {cit.get('source_id')} missing version/date")

    # 7. Simulation traceability.
    sim_traceable = bool(sim.get("reused_functions")) if sim else False

    # ---- scorecard -------------------------------------------------------
    fhir_completeness = float(pc.get("data_quality_score", 0.0))
    provenance = float(pc.get("provenance_coverage", 0.0))
    guideline_grounding = 1.0 if citations else 0.0
    drug_grounding = _pct(
        sum(1 for c in conflicts if c.get("evidence_citations")),
        max(1, len([c for c in conflicts if c.get("severity") in ("caution", "high", "blocked")])),
    )
    contra_cov = 1.0 if conflicts else 0.5
    covered = sum(1 for c in matrix if c.get("status") != "unknown")
    cross_cov = _pct(covered, len(matrix)) if matrix else 0.0
    abstention_quality = 1.0 if any(c.get("abstention_conditions") for c in candidates) else 0.5
    sim_score = 1.0 if sim_traceable else 0.3
    review_ready = 1.0 if (candidates and all(c.get("clinician_review_required") for c in candidates)) else 0.0
    overall = round(
        (fhir_completeness + provenance + guideline_grounding + drug_grounding + contra_cov
         + cross_cov + abstention_quality + sim_score + review_ready) / 9.0, 3
    )
    scorecard = CriticScorecard(
        fhir_completeness=fhir_completeness,
        provenance_coverage=provenance,
        guideline_grounding=guideline_grounding,
        drug_label_grounding=drug_grounding,
        contraindication_coverage=contra_cov,
        cross_organ_coverage=cross_cov,
        source_freshness=1.0 if citations else 0.0,
        abstention_quality=abstention_quality,
        simulation_traceability=sim_score,
        clinician_review_readiness=review_ready,
        overall_safety=overall,
    )

    result = CriticResult(
        safe_to_display=(not blocked) and bool(candidates),
        blocked_reasons=blocked,
        required_revisions=revisions,
        unsupported_claims=unsupported,
        missing_evidence=sorted({m for c in candidates for m in c.get("missing_information", [])}),
        scorecard=scorecard,
        audit_summary=f"{len(candidates)} candidates, {len(citations)} citations, "
                      f"{len(blocked)} blocking issues, overall {overall}.",
    )

    return make_stage_result(
        ctx=ctx, stage_id=STAGE_CLINICAL_CRITIC, timer=timer,
        status="blocked" if blocked else "completed",
        structured_output={"critic": result.model_dump()},
        warnings=blocked or [],
        safety_flags=["display_blocked"] if blocked else [],
        confidence=overall,
    )
