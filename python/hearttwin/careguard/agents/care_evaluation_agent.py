"""Care-Process Evaluation Harness (analysis-based).

Given (1) the doctor's report of what was done, (2) a patient-progress report, and
(3) CareGuard's own analysis for the case, this agent produces an ANALYSIS of how
well the documented care process aligned with the retrieved evidence: which flagged
contraindications/missing labs/cross-organ factors were addressed vs. not, plus a
structured process-quality scorecard and a progress summary.

This is quality-support analysis, NOT a punitive judgment and NOT a claim of
clinical correctness. It never diagnoses, doses, or prescribes. Every output reads
"Clinical decision support draft. Clinician review required." Deterministic-first;
Anthropic (when configured) only writes the narrative.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from python.hearttwin.careguard.reports import condition_mention_extractor as cme

DISCLAIMER = "Clinical decision support draft. Clinician review required."


class ProcessDimension(BaseModel):
    name: str
    score: float                       # 0..1, evidence-relative process alignment
    rationale: str
    addressed: list[str] = Field(default_factory=list)
    not_addressed: list[str] = Field(default_factory=list)
    evidence_source_ids: list[str] = Field(default_factory=list)


class CareEvaluation(BaseModel):
    case_id: str
    generated_at: str
    dimensions: list[ProcessDimension] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    analysis_suggestions: list[str] = Field(default_factory=list)
    patient_progress_summary: str = ""
    overall_process_quality: float = 0.0
    narrative: str = ""
    model_used: str | None = None
    clinician_review_required: bool = True
    safety_disclaimer: str = DISCLAIMER


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mentions(text: str, *terms: str) -> bool:
    low = (text or "").lower()
    return any(t.lower() in low for t in terms)


def _dim(name: str, addressed: list[str], missed: list[str], rationale: str,
         ev: list[str] | None = None) -> ProcessDimension:
    total = len(addressed) + len(missed)
    score = round(len(addressed) / total, 3) if total else 0.5
    return ProcessDimension(name=name, score=score, rationale=rationale,
                            addressed=addressed, not_addressed=missed, evidence_source_ids=ev or [])


def evaluate_process(
    *,
    case_id: str,
    artifacts: dict[str, Any],
    doctor_report: str,
    patient_progress: str,
) -> CareEvaluation:
    """Deterministic core: compare documented actions against CareGuard's analysis."""
    conflicts = artifacts.get("conflicts") or []
    med = artifacts.get("medication_safety") or {}
    med_conflicts = med.get("conflicts") or conflicts
    citations = artifacts.get("citations") or []
    context = artifacts.get("patient_context") or {}
    matrix = (artifacts.get("cross_organ_matrix") or {}).get("cells", [])
    missing = context.get("missing_critical_evidence") or []

    dims: list[ProcessDimension] = []

    # 1. Contraindication handling — were flagged high/blocked conflicts addressed?
    flagged = [c for c in med_conflicts if c.get("severity") in ("high_concern", "high", "blocked_for_draft", "blocked")]
    addr, miss = [], []
    for c in flagged:
        name = c.get("medication_name") or c.get("headline") or c.get("conflict_type", "conflict")
        key_terms = [str(c.get("medication_name") or ""), "potassium", "hyperkalemia", "renal"]
        (addr if _mentions(doctor_report, *[t for t in key_terms if t]) else miss).append(str(name))
    dims.append(_dim("contraindication_handling", addr, miss,
                     "Whether the documented actions acknowledge the flagged medication conflicts.",
                     [c.get("conflict_id", "") for c in flagged]))

    # 2. Missing-evidence handling (e.g. did the doctor obtain the missing potassium?).
    addr, miss = [], []
    for m in missing:
        (addr if _mentions(doctor_report, "potassium", "lab", "level", "obtained", "checked") and "potassium" in m.lower()
         else miss).append(m)
    dims.append(_dim("missing_evidence_addressed", addr, miss,
                     "Whether critical missing evidence was obtained or explicitly addressed."))

    # 3. Cross-organ consideration.
    organs = [c["domain"] for c in matrix if c.get("status") in ("caution", "high") and c["domain"] not in ("missing_evidence", "drug_interaction")]
    addr = [o for o in organs if _mentions(doctor_report, o, {"renal": "kidney", "pulmonary": "lung"}.get(o, o))]
    miss = [o for o in organs if o not in addr]
    dims.append(_dim("cross_organ_consideration", addr, miss,
                     "Whether documented care considered the comorbid organ systems CareGuard flagged."))

    # 4. Guideline alignment.
    orgs = [c.get("organization", "") for c in citations]
    addr = [o for o in orgs if o and _mentions(doctor_report, o.split("/")[0], "guideline", "gdmt")]
    dims.append(_dim("evidence_alignment", addr, [o for o in orgs if o not in addr],
                     "Whether documented care references the retrieved guideline evidence.",
                     [c.get("source_id", "") for c in citations]))

    # 5. Monitoring / follow-up.
    mon_addr = ["monitoring documented"] if _mentions(doctor_report, "monitor", "follow", "recheck", "repeat") else []
    dims.append(_dim("monitoring_and_followup", mon_addr,
                     [] if mon_addr else ["no monitoring/follow-up documented"],
                     "Whether a monitoring or follow-up plan is documented."))

    # 6. Documentation completeness.
    doc_addr = [x for x, present in (("what was done", bool(doctor_report.strip())),
                                     ("patient progress", bool(patient_progress.strip()))) if present]
    doc_miss = [x for x, present in (("what was done", bool(doctor_report.strip())),
                                     ("patient progress", bool(patient_progress.strip()))) if not present]
    dims.append(_dim("documentation_completeness", doc_addr, doc_miss,
                     "Whether both the care actions and the patient-progress note are present."))

    overall = round(sum(d.score for d in dims) / len(dims), 3) if dims else 0.0

    strengths = [f"{d.name.replace('_', ' ')}: addressed {', '.join(d.addressed)}"
                 for d in dims if d.addressed and d.score >= 0.5]
    gaps = [f"{d.name.replace('_', ' ')}: not addressed — {', '.join(d.not_addressed)}"
            for d in dims if d.not_addressed]
    suggestions = []
    for d in dims:
        if d.not_addressed:
            suggestions.append(f"Consider documenting how {', '.join(d.not_addressed)} was handled ({d.name.replace('_',' ')}).")

    progress_mentions = cme.extract(patient_progress)
    progress_summary = (patient_progress.strip()[:400] or "No patient-progress note supplied.")
    if progress_mentions:
        progress_summary += " | mentions: " + ", ".join(m.normalized_display for m in progress_mentions if m.normalized_display)

    evaluation = CareEvaluation(
        case_id=case_id, generated_at=_now(), dimensions=dims,
        strengths=strengths, gaps=gaps, analysis_suggestions=suggestions,
        patient_progress_summary=progress_summary, overall_process_quality=overall,
    )
    evaluation.narrative = _deterministic_narrative(evaluation)
    return evaluation


def _deterministic_narrative(ev: CareEvaluation) -> str:
    band = ("well-aligned" if ev.overall_process_quality >= 0.75
            else "partially aligned" if ev.overall_process_quality >= 0.5
            else "several gaps relative to the retrieved evidence")
    lead = (f"Analysis: the documented care process is {band} with CareGuard's evidence "
            f"(overall {round(ev.overall_process_quality*100)}%).")
    if ev.gaps:
        lead += " Key gaps: " + "; ".join(ev.gaps[:3]) + "."
    if ev.strengths:
        lead += " Strengths: " + "; ".join(ev.strengths[:2]) + "."
    return lead + f" {DISCLAIMER}"


async def enrich_narrative_with_anthropic(ev: CareEvaluation) -> CareEvaluation:
    """Optional: replace the narrative with an Anthropic analysis (deidentified,
    structured). Falls back to the deterministic narrative on any failure."""
    from python.hearttwin.careguard.anthropic import client
    from python.hearttwin.careguard.security import deidentify_for_model

    if not client.is_available():
        return ev

    class _Narr(BaseModel):
        narrative: str

    schema = {"type": "object", "properties": {"narrative": {"type": "string"}},
              "required": ["narrative"], "additionalProperties": False}
    payload = deidentify_for_model({
        "overall": ev.overall_process_quality,
        "dimensions": [d.model_dump() for d in ev.dimensions],
        "strengths": ev.strengths, "gaps": ev.gaps,
        "instruction": "Write a concise, analysis-based evaluation of how the documented care process "
                       "aligned with the evidence. Quality-support tone, not punitive. No diagnosis, no dosing.",
    })
    res = client.generate_structured(
        stage_id="clinical_critic",
        system="You are a clinical-quality analyst. Produce an evidence-relative, analysis-based process "
               "evaluation. Never diagnose, dose, or prescribe. End respecting the clinician-review disclaimer.",
        payload=payload, schema=schema, model_cls=_Narr,
    )
    if res.ok and res.obj:
        ev.narrative = f"{res.obj['narrative']} {DISCLAIMER}"
        ev.model_used = res.model_used
    return ev
