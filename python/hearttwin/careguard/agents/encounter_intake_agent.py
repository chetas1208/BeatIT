"""Agent 1 — Encounter Intake & Safety.

Verifies CareGuard is enabled, confirms the request is clinician-facing, blocks
consumer self-treatment / dosing / emergency-triage / autonomous-prescribing
intents, checks that facts exist, and establishes the safety framing. Deterministic.
"""

from __future__ import annotations

from python.hearttwin.careguard.agents.base import StageTimer, make_stage_result
from python.hearttwin.careguard.constants import (
    ALLOWED_INTENTS,
    CLINICIAN_REVIEW_LABEL,
    STAGE_ENCOUNTER_INTAKE,
    STAGE_FHIR_CONTEXT,
)
from python.hearttwin.careguard.feature_flags import careguard_enabled
from python.hearttwin.careguard.schemas import CareGuardContext, CareGuardStageResult

_BLOCK_PATTERNS = {
    "consumer_self_treatment": ("what should i take", "should i stop taking", "can i take", "self-medicate", "without a doctor"),
    "dose_generation": ("what dose", "how many mg", "calculate my dose", "dosage for me"),
    "emergency_triage": ("911", "emergency", "call an ambulance", "chest pain right now"),
    "autonomous_prescribing": ("prescribe for me", "write me a prescription", "auto-prescribe"),
}


def _classify(text: str, declared_intent: str) -> tuple[bool, str, list[str]]:
    low = (text or "").lower()
    flags: list[str] = []
    for blocked, patterns in _BLOCK_PATTERNS.items():
        if any(p in low for p in patterns):
            flags.append(f"blocked_intent:{blocked}")
            return False, blocked, flags
    intent = declared_intent if declared_intent in ALLOWED_INTENTS else "clinical_evidence_review"
    return True, intent, flags


async def run(ctx: CareGuardContext) -> CareGuardStageResult:
    timer = StageTimer()
    warnings: list[str] = []
    safety_flags: list[str] = []

    if not careguard_enabled():
        return make_stage_result(
            ctx=ctx, stage_id=STAGE_ENCOUNTER_INTAKE, timer=timer, status="blocked",
            structured_output={"allowed": False, "reason": "CareGuard is disabled"},
            safety_flags=["careguard_disabled"], confidence=0.0,
        )

    allowed, workflow, flags = _classify(ctx.clinical_question, ctx.workflow_intent)
    safety_flags.extend(flags)

    if not ctx.facts:
        warnings.append("No clinical facts available — import a FHIR bundle first.")

    if not allowed:
        return make_stage_result(
            ctx=ctx, stage_id=STAGE_ENCOUNTER_INTAKE, timer=timer, status="blocked",
            structured_output={
                "allowed": False,
                "workflow_type": workflow,
                "blocked_reason": f"Intent {workflow!r} is not permitted — CareGuard is a clinician-facing "
                                  "evidence-review tool. It does not self-treat, dose, triage, or prescribe.",
                "clinician_review_required": True,
            },
            safety_flags=safety_flags, warnings=warnings, confidence=1.0,
        )

    return make_stage_result(
        ctx=ctx, stage_id=STAGE_ENCOUNTER_INTAKE, timer=timer,
        status="completed" if ctx.facts else "warning",
        structured_output={
            "allowed": True,
            "workflow_type": workflow,
            "case_id": ctx.case_id,
            "run_id": ctx.run_id,
            "missing_resources": ctx.missing_resources,
            "next_stage": STAGE_FHIR_CONTEXT,
            "clinician_review_required": True,
            "safety_label": CLINICIAN_REVIEW_LABEL,
        },
        source_ids=[f.fact_id for f in ctx.facts[:20]],
        warnings=warnings, safety_flags=safety_flags, confidence=0.9 if ctx.facts else 0.5,
    )
