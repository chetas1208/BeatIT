"""Normalize parsed facts into a PatientContext (Agent 2's deterministic core).

Classifies conditions active/historical and cardiac/non-cardiac, reconstructs the
medication list, collects allergies/observations/procedures, and computes a
provenance-coverage + data-quality score. Never infers an unrecorded condition.
"""

from __future__ import annotations

from python.hearttwin.careguard.fhir.condition_extractor import is_cardiac
from python.hearttwin.careguard.fhir.parser import ParsedBundle
from python.hearttwin.careguard.schemas import ClinicalFact, PatientContext

_ACTIVE = {"active", "confirmed", "recurrence", "relapse", None}
_HISTORICAL = {"inactive", "resolved", "remission", "completed"}


def _is_active(fact: ClinicalFact) -> bool:
    return (fact.status or "").lower() not in _HISTORICAL


def build_patient_context(case_id: str, parsed: ParsedBundle) -> PatientContext:
    ctx = PatientContext(case_id=case_id)

    for f in parsed.facts:
        if f.category == "condition":
            cardiac = is_cardiac(str(f.display or ""), [{"code": f.code or "", "display": f.display or ""}])
            if cardiac and _is_active(f):
                ctx.active_cardiac_problem.append(f)
            elif cardiac:
                ctx.historical_cardiac_problems.append(f)
            else:
                ctx.active_non_cardiac_conditions.append(f)
        elif f.category == "medication":
            ctx.medications.append(f)
        elif f.category == "allergy":
            ctx.allergies.append(f)
        elif f.category == "observation":
            ctx.observations.append(f)
        elif f.category == "procedure":
            ctx.procedures.append(f)

    ctx.missing_critical_evidence = list(parsed.missing_critical_evidence)

    total = len(parsed.facts)
    with_provenance = sum(1 for f in parsed.facts if f.json_pointer)
    ctx.provenance_coverage = round(with_provenance / total, 3) if total else 0.0

    # Data quality: reward presence of the key elements for a cardiac review.
    have = 0.0
    if ctx.active_cardiac_problem:
        have += 0.35
    if ctx.medications:
        have += 0.25
    if ctx.observations:
        have += 0.2
    if ctx.allergies:
        have += 0.1
    if not ctx.missing_critical_evidence:
        have += 0.1
    ctx.data_quality_score = round(min(1.0, have), 3)
    return ctx
