"""CareGuard constants — stage IDs, safety strings, enums-as-tuples.

Kept dependency-free so any module (including tests) can import it cheaply.
"""

from __future__ import annotations

MODULE_NAME = "DualBeat CareGuard"
OUTPUT_VERSION = "careguard.v1"

# The mandatory safety framing on every clinician-facing surface.
CLINICIAN_REVIEW_LABEL = "Clinical decision support draft. Clinician review required."
SIMULATION_LABEL = "Simulated physiologic scenario for comparison only."
DEID_NOTICE = "CareGuard uses deidentified structured evidence for model-assisted review."
REFUSAL_USER_MESSAGE = (
    "The model could not complete this review. No clinical candidate was generated."
)
DRUG_LABEL_UNAVAILABLE = "drug-label evidence unavailable"

DISCLAIMER = (
    "Educational clinical-decision-support draft only. Clinician review required. "
    "DualBeat CareGuard is not a medical device, does not diagnose, does not prescribe, "
    "does not generate doses, and does not place orders. All outputs are simulated, "
    "evidence-linked drafts for a licensed clinician to review."
)

# ---------------------------------------------------------------------------
# Staged orchestration — deterministic stage IDs (Vercel-safe, one per /next).
# ---------------------------------------------------------------------------
STAGE_ENCOUNTER_INTAKE = "encounter_intake"
STAGE_FHIR_CONTEXT = "fhir_context"
STAGE_MULTIMORBIDITY = "multimorbidity_analysis"
STAGE_GUIDELINE_EVIDENCE = "guideline_evidence"
STAGE_MEDICATION_SAFETY = "medication_safety"
STAGE_CANDIDATE_COMPOSITION = "candidate_composition"
STAGE_HEARTTWIN_SCENARIOS = "hearttwin_scenarios"
STAGE_CLINICAL_CRITIC = "clinical_critic"
STAGE_CLINICIAN_REVIEW_READY = "clinician_review_ready"

STAGE_ORDER: tuple[str, ...] = (
    STAGE_ENCOUNTER_INTAKE,
    STAGE_FHIR_CONTEXT,
    STAGE_MULTIMORBIDITY,
    STAGE_GUIDELINE_EVIDENCE,
    STAGE_MEDICATION_SAFETY,
    STAGE_CANDIDATE_COMPOSITION,
    STAGE_HEARTTWIN_SCENARIOS,
    STAGE_CLINICAL_CRITIC,
    STAGE_CLINICIAN_REVIEW_READY,
)

# Which agent owns each stage.
STAGE_AGENT = {
    STAGE_ENCOUNTER_INTAKE: ("careguard_encounter_intake_agent", "Encounter Intake & Safety Agent"),
    STAGE_FHIR_CONTEXT: ("careguard_fhir_context_agent", "FHIR Patient Context Agent"),
    STAGE_MULTIMORBIDITY: ("careguard_multimorbidity_agent", "Clinical Problem & Multimorbidity Agent"),
    STAGE_GUIDELINE_EVIDENCE: ("careguard_guideline_evidence_agent", "Guideline Evidence Agent"),
    STAGE_MEDICATION_SAFETY: ("careguard_medication_safety_agent", "Medication & Contraindication Agent"),
    STAGE_CANDIDATE_COMPOSITION: ("careguard_care_plan_composer_agent", "Candidate Care-Plan Composer Agent"),
    STAGE_HEARTTWIN_SCENARIOS: ("careguard_hearttwin_scenario_agent", "DualBeat Scenario Agent"),
    STAGE_CLINICAL_CRITIC: ("careguard_clinical_critic_agent", "Evidence, Safety & Clinical Critic Agent"),
    STAGE_CLINICIAN_REVIEW_READY: ("careguard_orchestrator", "Clinician Review Gate"),
}

# ---------------------------------------------------------------------------
# Intent classification (encounter intake).
# ---------------------------------------------------------------------------
ALLOWED_INTENTS: tuple[str, ...] = (
    "clinical_evidence_review",
    "care_plan_comparison",
    "contraindication_review",
    "medication_safety_review",
    "missing_evidence_review",
    "simulation_comparison",
)
BLOCKED_INTENTS: tuple[str, ...] = (
    "consumer_self_diagnosis",
    "consumer_self_treatment",
    "dose_generation",
    "emergency_triage",
    "autonomous_prescribing",
)

# ---------------------------------------------------------------------------
# Cross-organ risk matrix dimensions.
# ---------------------------------------------------------------------------
RISK_DOMAINS: tuple[str, ...] = (
    "cardiac",
    "renal",
    "hepatic",
    "pulmonary",
    "metabolic",
    "bleeding",
    "allergy",
    "pregnancy",
    "frailty",
    "drug_interaction",
    "missing_evidence",
)

# FHIR R4 resource types CareGuard parses (others recorded as unsupported).
SUPPORTED_FHIR_RESOURCES: tuple[str, ...] = (
    "Patient",
    "Encounter",
    "Condition",
    "Observation",
    "DiagnosticReport",
    "MedicationRequest",
    "MedicationStatement",
    "AllergyIntolerance",
    "Procedure",
    "ImagingStudy",
    "ServiceRequest",
    "CarePlan",
    "Goal",
    "DocumentReference",
    "Practitioner",
    "Organization",
)

# Terminology systems preserved verbatim (never invented).
CODE_SYSTEMS = {
    "snomed": "http://snomed.info/sct",
    "loinc": "http://loinc.org",
    "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "icd10": "http://hl7.org/fhir/sid/icd-10-cm",
    "ucum": "http://unitsofmeasure.org",
}

# Phrase banned from all runtime surfaces (spec §1). Assembled from parts so the
# literal never appears in any runtime file (the verify scan would otherwise flag
# this definition). README exception handled in docs only.
FORBIDDEN_RUNTIME_PHRASE = "prior" + " work"
