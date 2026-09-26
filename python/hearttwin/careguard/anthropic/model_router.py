"""Route a CareGuard stage/role to an Anthropic model + retention policy."""

from __future__ import annotations

from python.hearttwin.careguard import config as cg_config
from python.hearttwin.careguard.config import DEIDENTIFY_ONLY_MODELS

# Stage role → model config key.
STAGE_ROLE = {
    "encounter_intake": "fast",
    "fhir_context": "fhir",
    "multimorbidity_analysis": "multimorbidity",
    "guideline_evidence": "guidelines",
    "medication_safety": "medication_safety",
    "candidate_composition": "plan_composer",
    "hearttwin_scenarios": "fast",
    "clinical_critic": "clinical_critic",
}


def model_for_stage(stage_id: str) -> str:
    return cg_config.model_for(STAGE_ROLE.get(stage_id, "fallback"))


def fallback_model() -> str:
    return cg_config.model_for("fallback")


def is_deidentify_only(model: str) -> bool:
    """True if this model must only ever receive deidentified structured facts."""
    return model in DEIDENTIFY_ONLY_MODELS


def requires_deidentification(model: str) -> bool:
    from python.hearttwin.careguard.feature_flags import require_deidentification

    return require_deidentification() or is_deidentify_only(model)
