"""Agent 2 — FHIR Patient Context.

Builds the normalized PatientContext from recorded facts (deterministic
normalizer). Never infers an unrecorded condition; reports provenance coverage
and missing evidence.
"""

from __future__ import annotations

from python.hearttwin.careguard.agents.base import StageTimer, make_stage_result
from python.hearttwin.careguard.constants import STAGE_FHIR_CONTEXT
from python.hearttwin.careguard.fhir.normalizer import build_patient_context
from python.hearttwin.careguard.fhir.parser import ParsedBundle
from python.hearttwin.careguard.fhir.bundle_validator import ValidationSummary
from python.hearttwin.careguard.schemas import CareGuardContext, CareGuardStageResult


async def run(ctx: CareGuardContext) -> CareGuardStageResult:
    timer = StageTimer()

    # Rebuild a minimal ParsedBundle view from the threaded facts (context is
    # stateless between serverless calls — facts come from persisted case state).
    parsed = ParsedBundle(
        bundle_id=ctx.prior_stage_outputs.get("bundle_id", "bundle"),
        validation=ValidationSummary(valid=True),
        facts=ctx.facts,
        missing_critical_evidence=ctx.missing_resources,
    )
    patient_context = build_patient_context(ctx.case_id, parsed)

    warnings: list[str] = []
    if patient_context.missing_critical_evidence:
        warnings.extend(patient_context.missing_critical_evidence)

    status = "completed"
    if patient_context.provenance_coverage < 1.0:
        warnings.append(f"provenance coverage {patient_context.provenance_coverage}")
    if not patient_context.active_cardiac_problem:
        status = "warning"
        warnings.append("No active cardiac problem recorded.")

    return make_stage_result(
        ctx=ctx, stage_id=STAGE_FHIR_CONTEXT, timer=timer, status=status,
        structured_output={"patient_context": patient_context.model_dump()},
        source_ids=[f.fact_id for f in ctx.facts],
        missing_information=patient_context.missing_critical_evidence,
        warnings=warnings,
        confidence=round(0.4 + 0.6 * patient_context.provenance_coverage, 3),
    )
