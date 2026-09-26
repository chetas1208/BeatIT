export type SensitivityMethod =
  | "local"
  | "finite_difference"
  | "sobol"
  | "shapley"
  | "other";

export type DifferenceScheme = "central" | "forward" | "backward" | "unavailable";

export type ProvenanceSource =
  | "deterministic_model"
  | "ensemble"
  | "shadow_trial"
  | "derived";

export type MissingPieceRequest = {
  baseline_ensemble_id: string;
  target_metric: string;
  available_evidence_types?: string[];
};

export type SensitivityProvenance = {
  source: ProvenanceSource;
  analysis_id?: string | null;
  ensemble_id?: string | null;
  shadow_trial_id?: string | null;
  sample_count?: number | null;
  seed?: number | null;
  model_version: string;
  assumptions: string[];
};

export type ParameterSensitivity = {
  parameter_id: string;
  metric_id: string;
  method: SensitivityMethod;
  sensitivity: number;
  baseline_value: number;
  perturbation?: number | null;
  normalized_sensitivity?: number | null;
  difference_scheme?: DifferenceScheme | null;
  available: boolean;
  provenance: SensitivityProvenance;
};

export type ParameterUncertaintyImpact = {
  parameter_id: string;
  metric_id: string;
  uncertainty_magnitude: number;
  sensitivity_magnitude: number;
  impact_score: number;
  normalized_impact?: number | null;
  method: string;
};

export type EvidenceValueEstimate = {
  evidence_type: string;
  target_metric: string;
  constrained_parameters: string[];
  estimated_reduction?: number | null;
  ranking_score: number;
  method: string;
  assumptions: string[];
  provenance: {
    source: ProvenanceSource;
    evidence_map_version: string;
    analysis_id?: string | null;
    assumptions: string[];
  };
};

export type EvidenceConstraint = {
  evidence_type: string;
  constrained_parameters: string[];
  strength: "direct" | "strong" | "moderate" | "weak";
  rationale: string;
  source: string;
};

export type MissingPieceCompleteness = {
  method: string;
  target_metric: string | null;
  parameter_count: number;
  parameter_ids: string[];
  covered_parameter_count: number;
  coverage_fraction: number;
  declared_covered_parameters: string[];
  declared_coverage_fraction: number;
  declared_complete: boolean;
  mapped_evidence: Record<string, string[]>;
  available_evidence: Record<string, string[]>;
  available_covered_parameters: string[];
  available_coverage_fraction: number;
  uncovered_parameters: string[];
  unavailable_evidence_parameters: string[];
  complete: boolean;
  limitations: string[];
};

export type MissingPieceResponse = {
  target_metric: string;
  sensitivities: ParameterSensitivity[];
  dominant_uncertainty_drivers: ParameterUncertaintyImpact[];
  evidence_ranking: EvidenceValueEstimate[];
  evidence_constraints: EvidenceConstraint[];
  completeness: MissingPieceCompleteness;
  limitations: string[];
  provenance: {
    source: ProvenanceSource;
    analysis_id: string;
    ensemble_id?: string | null;
    shadow_trial_id?: string | null;
    sensitivity_method: string;
    ranking_method: string;
    model_version: string;
    assumptions: string[];
  };
  safety_disclaimer: string;
};
