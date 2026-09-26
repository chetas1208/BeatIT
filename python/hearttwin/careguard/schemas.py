"""CareGuard Pydantic schemas — strict contracts for every artifact.

These are additive and independent of DualBeat's ``schemas.py`` (never
overwrite it). Model outputs are validated against these before entering state;
malformed model output is rejected, never coerced from prose.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from python.hearttwin.careguard.constants import OUTPUT_VERSION

AssertionType = Literal["recorded", "derived_deterministically", "model_inference", "missing"]
StageStatus = Literal["completed", "warning", "blocked", "failed", "skipped"]
Severity = Literal["informational", "caution", "high", "blocked"]


# ---------------------------------------------------------------------------
# Provenance-bearing clinical fact (spec §9).
# ---------------------------------------------------------------------------
class ClinicalFact(BaseModel):
    fact_id: str
    category: str
    value: str | float | bool | None = None
    unit: Optional[str] = None
    code_system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None
    status: Optional[str] = None
    effective_at: Optional[str] = None
    resource_type: str
    resource_id: str
    json_pointer: str
    source_bundle_id: str
    confidence: float = 1.0
    assertion_type: AssertionType = "recorded"


# ---------------------------------------------------------------------------
# Evidence citation (spec §10, Agent 4).
# ---------------------------------------------------------------------------
class EvidenceCitation(BaseModel):
    source_id: str
    organization: str
    title: str
    version: Optional[str] = None
    publication_date: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    passage: str
    recommendation_class: Optional[str] = None
    evidence_level: Optional[str] = None
    local_path: Optional[str] = None
    canonical_source: Optional[str] = None
    sha256: Optional[str] = None
    retrieved_at: str
    authority_level: Optional[int] = None
    document_type: Optional[str] = None
    synthetic_excerpt: Optional[bool] = None


# ---------------------------------------------------------------------------
# Medication conflict (spec §10, Agent 5).
# ---------------------------------------------------------------------------
class MedicationConflict(BaseModel):
    medication_name: str
    rxcui: Optional[str] = None
    conflict_type: str
    severity: Severity = "informational"
    patient_fact_ids: list[str] = Field(default_factory=list)
    evidence_citations: list[EvidenceCitation] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    statement: str
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# Candidate care plan (spec §10, Agent 6).
# ---------------------------------------------------------------------------
class MonitoringConsideration(BaseModel):
    parameter: str
    rationale: str
    evidence_source_id: Optional[str] = None


class CandidateCarePlan(BaseModel):
    candidate_id: str
    title: str
    description: str
    guideline_basis: list[EvidenceCitation] = Field(default_factory=list)
    matching_patient_fact_ids: list[str] = Field(default_factory=list)
    unmatched_or_unknown_criteria: list[str] = Field(default_factory=list)
    contraindications: list[MedicationConflict] = Field(default_factory=list)
    drug_interactions: list[MedicationConflict] = Field(default_factory=list)
    cross_organ_considerations: dict[str, list[str]] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    monitoring_considerations: list[dict] = Field(default_factory=list)
    follow_up_window: Optional[dict] = None
    reasons_for: list[str] = Field(default_factory=list)
    reasons_against: list[str] = Field(default_factory=list)
    abstention_conditions: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    clinician_review_required: Literal[True] = True


# ---------------------------------------------------------------------------
# Normalized patient context (spec §9, Agent 2 output).
# ---------------------------------------------------------------------------
class PatientContext(BaseModel):
    case_id: str
    active_cardiac_problem: list[ClinicalFact] = Field(default_factory=list)
    historical_cardiac_problems: list[ClinicalFact] = Field(default_factory=list)
    active_non_cardiac_conditions: list[ClinicalFact] = Field(default_factory=list)
    medications: list[ClinicalFact] = Field(default_factory=list)
    allergies: list[ClinicalFact] = Field(default_factory=list)
    observations: list[ClinicalFact] = Field(default_factory=list)
    procedures: list[ClinicalFact] = Field(default_factory=list)
    diagnostic_reports: list[ClinicalFact] = Field(default_factory=list)
    missing_critical_evidence: list[str] = Field(default_factory=list)
    provenance_coverage: float = 0.0
    data_quality_score: float = 0.0


# ---------------------------------------------------------------------------
# Cross-organ risk matrix (spec §10, Agent 3).
# ---------------------------------------------------------------------------
class RiskCell(BaseModel):
    domain: str
    status: Literal["ok", "caution", "high", "blocked", "unknown", "not_applicable"] = "unknown"
    factors: list[str] = Field(default_factory=list)
    patient_fact_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    note: str = ""


class CrossOrganMatrix(BaseModel):
    case_id: str
    cells: list[RiskCell] = Field(default_factory=list)
    review_scope: str = ""


# ---------------------------------------------------------------------------
# Critic scorecard (spec §10, Agent 8).
# ---------------------------------------------------------------------------
class CriticScorecard(BaseModel):
    fhir_completeness: float = 0.0
    provenance_coverage: float = 0.0
    guideline_grounding: float = 0.0
    drug_label_grounding: float = 0.0
    contraindication_coverage: float = 0.0
    cross_organ_coverage: float = 0.0
    source_freshness: float = 0.0
    abstention_quality: float = 0.0
    simulation_traceability: float = 0.0
    clinician_review_readiness: float = 0.0
    overall_safety: float = 0.0


class CriticResult(BaseModel):
    safe_to_display: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    required_revisions: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    scorecard: CriticScorecard = Field(default_factory=CriticScorecard)
    audit_summary: str = ""


# ---------------------------------------------------------------------------
# Uniform stage result (spec §10).
# ---------------------------------------------------------------------------
class CareGuardStageResult(BaseModel):
    run_id: str
    case_id: str
    stage_id: str
    agent_id: str
    agent_name: str
    model_used: Optional[str] = None
    status: StageStatus
    started_at: str
    completed_at: str
    latency_ms: int = 0
    source_ids: list[str] = Field(default_factory=list)
    tools_called: list[dict] = Field(default_factory=list)
    structured_output: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    audit_event_ids: list[str] = Field(default_factory=list)
    output_version: str = OUTPUT_VERSION


# ---------------------------------------------------------------------------
# Agent input context.
# ---------------------------------------------------------------------------
class CareGuardContext(BaseModel):
    """Shared input threaded through the staged pipeline. Deidentified structured
    facts only — never raw bundle, raw notes, or images."""
    run_id: str
    case_id: str
    workflow_intent: str = "clinical_evidence_review"
    stage_id: str = ""
    clinical_question: str = ""
    facts: list[ClinicalFact] = Field(default_factory=list)
    patient_context: Optional[PatientContext] = None
    cross_organ_matrix: Optional[CrossOrganMatrix] = None
    guideline_citations: list[EvidenceCitation] = Field(default_factory=list)
    medication_conflicts: list[MedicationConflict] = Field(default_factory=list)
    candidates: list[CandidateCarePlan] = Field(default_factory=list)
    simulation: Optional[dict] = None
    prior_stage_outputs: dict[str, Any] = Field(default_factory=dict)
    missing_resources: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Run + case records.
# ---------------------------------------------------------------------------
RunStatus = Literal["created", "running", "blocked", "completed", "failed", "cancelled"]


class CareGuardRun(BaseModel):
    run_id: str
    case_id: str
    status: RunStatus = "created"
    workflow_intent: str = "clinical_evidence_review"
    current_stage: str = ""
    next_stage: Optional[str] = None
    completed_stages: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    stage_results: list[CareGuardStageResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    persisted: bool = False
    disclaimer: str = ""


class CareGuardCase(BaseModel):
    case_id: str
    source_bundle_id: Optional[str] = None
    fixture_id: Optional[str] = None
    deidentified: bool = True
    created_at: str
    clinical_question: str = ""
    facts: list[ClinicalFact] = Field(default_factory=list)
    unsupported_resources: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API request bodies.
# ---------------------------------------------------------------------------
class FhirImportRequest(BaseModel):
    bundle: Optional[dict] = None
    fixture_id: Optional[str] = None
    clinical_question: str = ""


class CreateRunRequest(BaseModel):
    case_id: str
    workflow_intent: str = "clinical_evidence_review"
    clinical_question: str = ""


class FeedbackRequest(BaseModel):
    decision: Literal["accept_for_draft", "reject", "request_more_information", "override"]
    candidate_id: Optional[str] = None
    reason: str = ""
    reviewer_role: str = "clinician"


class AuditEvent(BaseModel):
    event_id: str
    case_id: str
    run_id: Optional[str] = None
    stage_id: Optional[str] = None
    actor: str
    action: str
    detail: dict = Field(default_factory=dict)
    created_at: str
