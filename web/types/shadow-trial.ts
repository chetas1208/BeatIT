import type { CardiacTwinState } from "@/types/heart";

export type ShadowTrialMetricId =
  | "ejection_fraction_pct"
  | "stroke_volume_ml"
  | "cardiac_output_l_min"
  | "heart_rate_bpm"
  | "map_mmhg"
  | "edv_ml"
  | "esv_ml"
  | "pv_loop_area_index";

export interface ShadowTrialScenarioParameter {
  parameter: string;
  baseline?: number;
  value: number;
  delta?: number;
  unit?: string;
}

export interface ShadowTrialScenarioDefinition {
  id: string;
  label: string;
  description?: string | null;
  origin_snapshot_id?: string | null;
  parameters: ShadowTrialScenarioParameter[];
  created_at?: string | null;
}

export interface ShadowTrialRequest {
  baseline_ensemble_id: string;
  scenario: ShadowTrialScenarioDefinition;
  metrics?: ShadowTrialMetricId[];
}

export interface ShadowTrialDefinition {
  id: string;
  origin_snapshot_id: string;
  baseline_ensemble_id: string;
  scenario: ShadowTrialScenarioDefinition;
  metrics: ShadowTrialMetricId[];
  created_at: string;
  provenance: Record<string, unknown>;
}

export interface ShadowTrialEffectDistribution {
  metric_id: ShadowTrialMetricId;
  unit: string;
  deltas: number[];
  mean_delta: number | null;
  median_delta: number | null;
  quantiles: { q05: number | null; q25: number | null; q75: number | null; q95: number | null };
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  neutral_tolerance: number;
}

export interface ShadowTrialPair {
  sample_id: string;
  baseline_twin_id: string;
  scenario_twin_id: string;
  baseline_state: CardiacTwinState;
  scenario_state: CardiacTwinState;
  baseline_parameters: Record<string, number>;
  scenario_parameters: Record<string, number>;
  parameters: Record<string, number>;
  deltas: Partial<Record<ShadowTrialMetricId, number>>;
  delta_units: Record<string, string>;
  valid: boolean;
  rejection_reasons: string[];
}

export interface ShadowTrialResponse {
  id: string;
  definition_id: string;
  baseline_ensemble_id: string;
  requested_pairs: number;
  valid_pairs: number;
  invalid_pairs: number;
  paired_results: ShadowTrialPair[];
  effect_distributions: ShadowTrialEffectDistribution[];
  provenance: Record<string, unknown>;
  warnings: string[];
  status: "complete" | "failed";
  fingerprint: string;
  safety_disclaimer: string;
  definition?: ShadowTrialDefinition | null;
}

export interface ShadowTrialEffectsResponse {
  trial_id: string;
  definition_id: string;
  baseline_ensemble_id: string;
  requested_pairs: number;
  valid_pairs: number;
  invalid_pairs: number;
  effect_distributions: ShadowTrialEffectDistribution[];
  warnings: string[];
  safety_disclaimer: string;
}

export interface ShadowTrialPairResponse {
  trial_id: string;
  pair: ShadowTrialPair;
  safety_disclaimer: string;
}
