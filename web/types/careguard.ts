// CareGuard + Multimorbidity Medication Safety frontend types.
// Mirror of the Python Pydantic contracts (subset the UI consumes).

export interface ClinicalFact {
  fact_id: string;
  category: string;
  value: string | number | boolean | null;
  unit?: string | null;
  code_system?: string | null;
  code?: string | null;
  display?: string | null;
  status?: string | null;
  json_pointer: string;
  assertion_type: string;
}

export interface PatientContext {
  case_id: string;
  active_cardiac_problem: ClinicalFact[];
  historical_cardiac_problems: ClinicalFact[];
  active_non_cardiac_conditions: ClinicalFact[];
  medications: ClinicalFact[];
  allergies: ClinicalFact[];
  observations: ClinicalFact[];
  procedures: ClinicalFact[];
  missing_critical_evidence: string[];
  provenance_coverage: number;
  data_quality_score: number;
}

export interface EvidenceCitation {
  source_id: string;
  organization: string;
  title: string;
  version?: string | null;
  section?: string | null;
  passage: string;
  recommendation_class?: string | null;
  evidence_level?: string | null;
  canonical_source?: string | null;
  sha256?: string | null;
  synthetic_excerpt?: boolean | null;
}

export interface RiskCell {
  domain: string;
  status: string;
  factors: string[];
  missing_evidence: string[];
  note: string;
}

export interface StageResult {
  stage_id: string;
  agent_name: string;
  status: string;
  confidence: number;
  warnings: string[];
  model_used?: string | null;
}

export interface CareGuardRun {
  run_id: string;
  case_id: string;
  status: string;
  current_stage: string;
  next_stage?: string | null;
  completed_stages: string[];
  stage_results: StageResult[];
}

export interface MedicationEvidence {
  source_type: string;
  authority_tier: string;
  source_title: string;
  section?: string | null;
  exact_passage?: string | null;
  effective_date?: string | null;
  source_version?: string | null;
}

export interface MedicationSafetyConflict {
  conflict_id: string;
  conflict_type: string;
  severity: string;
  headline: string;
  clinical_statement: string;
  authoritative_evidence: MedicationEvidence[];
  supplemental_evidence: MedicationEvidence[];
  missing_information: string[];
  requires_pharmacist_review: boolean;
}

export interface MedicationIdentity {
  medication_id: string;
  original_text: string;
  rxcui?: string | null;
  ingredients: string[];
  status: string;
  normalization_warnings: string[];
}

export interface AlternativeCandidate {
  candidate_id: string;
  medication_identity: MedicationIdentity;
  alternative_type: string;
  display_status: string;
  guideline_evidence: MedicationEvidence[];
  reasons_considered: string[];
  unresolved_questions: string[];
  conflict_burden_score: number;
  evidence_completeness_score: number;
}

export interface ConditionMention {
  mention_id: string;
  normalized_display?: string | null;
  status: string;
  temporality: string;
  experiencer: string;
  exact_snippet: string;
}

export interface MedicationSafety {
  overall_status: string;
  reconciled_active_medications: MedicationIdentity[];
  confirmed_conditions: Record<string, unknown>[];
  report_mentions_requiring_confirmation: ConditionMention[];
  conflicts: MedicationSafetyConflict[];
  alternative_candidates: AlternativeCandidate[];
  missing_information: string[];
  medication_reconciliation_score: number;
  safety_disclaimer: string;
}
