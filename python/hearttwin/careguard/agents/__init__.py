"""The eight CareGuard agents (separate from DualBeat's eight agents).

Each exposes ``async def run(ctx: CareGuardContext) -> CareGuardStageResult`` and
is deterministic-first: it produces valid structured output WITHOUT an Anthropic
key, using Claude only as an optional prose/enhancement layer when available.
"""

from __future__ import annotations

__all__ = [
    "encounter_intake_agent",
    "fhir_context_agent",
    "multimorbidity_agent",
    "guideline_evidence_agent",
    "medication_safety_agent",
    "care_plan_composer_agent",
    "hearttwin_scenario_agent",
    "clinical_critic_agent",
]
