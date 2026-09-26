"""Schemas for the Multimorbidity Medication Safety engine.

Additive to CareGuard's core schemas. Enforced via Pydantic before any model
output enters state. Terminology is deliberately conservative: no field can say
a medication is "safe", "best", or "optimal".
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

AuthorityTier = Literal["A", "B", "C"]

EvidenceSource = Literal[
    "dailymed_spl", "openfda_label", "orange_book", "clinical_guideline",
    "rxnorm", "rxclass", "ddinter", "drugcentral", "sider",
    "licensed_drugbank", "local_approved_document",
]

EvidenceSupports = Literal[
    "contraindication", "warning", "interaction", "organ_consideration",
    "indication", "therapeutic_class", "generic_equivalence",
    "adverse_reaction", "supplemental_signal",
]

ConflictType = Literal[
    "documented_contraindication", "drug_drug_interaction", "drug_disease_interaction",
    "drug_organ_function_concern", "allergy_conflict", "therapeutic_duplication",
    "monitoring_gap", "possible_report_morbidity", "insufficient_evidence",
]

Severity = Literal[
    "blocked_for_draft", "high_concern", "caution", "informational", "insufficient_evidence",
]

MentionStatus = Literal[
    "possible_report_mention", "negated_report_mention", "family_history",
    "ruled_out", "uncertain",
]

MedStatus = Literal["active", "proposed", "historical", "stopped", "unknown"]

AlternativeType = Literal[
    "generic_equivalent", "same_guideline_supported_class",
    "cross_class_guideline_candidate", "ddinter_lead_verified",
    "non_medication_strategy_from_guideline",
]

DisplayStatus = Literal[
    "candidate_for_clinician_review", "requires_more_information",
    "excluded_due_to_conflict", "insufficient_evidence",
]

OverallStatus = Literal[
    "no_documented_conflict_found", "review_required", "high_concern",
    "blocked_for_draft", "insufficient_evidence",
]


class MedicationEvidence(BaseModel):
    evidence_id: str
    source_type: EvidenceSource
    authority_tier: AuthorityTier
    source_title: str
    source_version: Optional[str] = None
    effective_date: Optional[str] = None
    retrieved_at: str
    section: Optional[str] = None
    exact_passage: Optional[str] = None
    source_identifier: Optional[str] = None
    local_snapshot_path: Optional[str] = None
    source_hash: Optional[str] = None
    supports: EvidenceSupports
    confidence: float = 0.5


class MedicationIdentity(BaseModel):
    medication_id: str
    original_text: str
    normalized_name: Optional[str] = None
    rxcui: Optional[str] = None
    ingredient_rxcuis: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    brand_name: Optional[str] = None
    dose_form: Optional[str] = None
    strength_text: Optional[str] = None
    route: Optional[str] = None
    status: MedStatus = "unknown"
    source_resource_type: str = ""
    source_resource_id: str = ""
    provenance_pointer: str = ""
    normalization_confidence: float = 0.0
    normalization_warnings: list[str] = Field(default_factory=list)
    candidate_rxcuis: list[str] = Field(default_factory=list)


class ConditionMention(BaseModel):
    mention_id: str
    raw_text: str
    normalized_display: Optional[str] = None
    code_system: Optional[str] = None
    code: Optional[str] = None
    status: MentionStatus
    temporality: Literal["current", "historical", "future", "unknown"] = "unknown"
    experiencer: Literal["patient", "family", "other", "unknown"] = "unknown"
    source_document_id: str = ""
    page: Optional[int] = None
    section: Optional[str] = None
    exact_snippet: str = ""
    confidence: float = 0.5


class MedicationSafetyConflict(BaseModel):
    conflict_id: str
    proposed_medication_id: str
    interacting_medication_ids: list[str] = Field(default_factory=list)
    patient_fact_ids: list[str] = Field(default_factory=list)
    conflict_type: ConflictType
    severity: Severity
    headline: str
    clinical_statement: str
    mechanism_summary: Optional[str] = None
    authoritative_evidence: list[MedicationEvidence] = Field(default_factory=list)
    supplemental_evidence: list[MedicationEvidence] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    clinician_actions: list[str] = Field(default_factory=list)
    can_display: bool = True
    requires_clinician_confirmation: bool = False
    requires_pharmacist_review: bool = False
    confidence: float = 0.5


class MedicationAlternativeCandidate(BaseModel):
    candidate_id: str
    original_proposed_medication_id: str
    medication_identity: MedicationIdentity
    alternative_type: AlternativeType
    indication_under_review: str = ""
    guideline_evidence: list[MedicationEvidence] = Field(default_factory=list)
    label_evidence: list[MedicationEvidence] = Field(default_factory=list)
    reasons_considered: list[str] = Field(default_factory=list)
    documented_conflicts: list[MedicationSafetyConflict] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    evidence_completeness_score: float = 0.0
    conflict_burden_score: float = 0.0
    source_freshness_score: float = 0.0
    display_status: DisplayStatus = "requires_more_information"
    clinician_review_required: Literal[True] = True
    pharmacist_review_recommended: bool = True


class MedicationSafetyCriticOutput(BaseModel):
    safe_to_display: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_sources: list[str] = Field(default_factory=list)
    unverified_alternatives: list[str] = Field(default_factory=list)
    hidden_uncertainty: list[str] = Field(default_factory=list)
    required_revisions: list[str] = Field(default_factory=list)


class MultimorbidityMedicationSafetyOutput(BaseModel):
    case_id: str
    run_id: str = ""
    proposed_medications: list[MedicationIdentity] = Field(default_factory=list)
    reconciled_active_medications: list[MedicationIdentity] = Field(default_factory=list)
    confirmed_conditions: list[dict] = Field(default_factory=list)
    historical_conditions: list[dict] = Field(default_factory=list)
    report_mentions_requiring_confirmation: list[ConditionMention] = Field(default_factory=list)
    conflicts: list[MedicationSafetyConflict] = Field(default_factory=list)
    alternative_candidates: list[MedicationAlternativeCandidate] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    clinician_confirmation_requests: list[str] = Field(default_factory=list)
    overall_status: OverallStatus = "review_required"
    evidence_coverage_score: float = 0.0
    provenance_coverage_score: float = 0.0
    medication_reconciliation_score: float = 0.0
    critic_findings: list[str] = Field(default_factory=list)
    safety_disclaimer: str = ""


class MedicationReviewRequest(BaseModel):
    proposed_medication: Optional[dict] = None
    proposed_medication_request_id: Optional[str] = None
    clinical_question: str = ""
    include_alternatives: bool = True
    require_guideline_grounding: bool = True
