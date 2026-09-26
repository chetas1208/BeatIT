import type { CardiacTwinState } from "@/types/heart";
import type { SnapshotQuality, TwinProvenance } from "@/lib/twin/time/contracts";

export type EnsembleParameterId = "heart_rate_bpm" | "preload_index" | "afterload_index" | "contractility_index" | "systemic_vascular_resistance_index";
export type EnsembleMetricId = "ejection_fraction_pct" | "stroke_volume_ml" | "cardiac_output_l_min" | "heart_rate_bpm";

export interface EnsembleApiRequestDistribution {
  parameter_id: EnsembleParameterId;
  family: "fixed" | "normal" | "lognormal" | "uniform" | "empirical";
  parameters: Record<string, number | number[]>;
  bounds: { min: number; max: number };
  source: "measurement" | "derived" | "population_prior" | "expert_prior" | "scenario";
  evidence_ids: string[];
  rationale: string;
  version: string;
}

export interface EnsembleApiRequest {
  origin_snapshot_id: string;
  state: CardiacTwinState;
  seed: number;
  sample_count: number;
  distributions: EnsembleApiRequestDistribution[];
  physiology_version: string;
  distribution_config_version: string;
  prior_version: string;
  origin_quality: SnapshotQuality;
  parent_scenario_id?: string;
  origin_provenance: TwinProvenance[];
  evidence_ids: string[];
}

export interface EnsembleApiSample {
  id: string;
  index: number;
  seed: number;
  origin_snapshot_id: string;
  origin_quality: SnapshotQuality;
  parameters: Record<string, number>;
  outputs: Record<string, number>;
  state: CardiacTwinState;
  valid: boolean;
  rejection_reasons: string[];
}

export interface EnsembleApiMetricDistribution {
  metric_id: EnsembleMetricId;
  unit: string;
  samples: number[];
  mean: number;
  median: number;
  variance: number;
  standard_deviation: number;
  quantiles: { q05: number; q25: number; q75: number; q95: number };
  min: number;
  max: number;
}

export interface EnsembleApiResponse {
  id: string;
  origin_snapshot_id: string;
  seed: number;
  requested_sample_count: number;
  accepted_sample_count: number;
  rejected_sample_count: number;
  samples: EnsembleApiSample[];
  distributions: EnsembleApiMetricDistribution[];
  parameter_distributions: EnsembleApiRequestDistribution[];
  provenance: {
    origin_snapshot_id: string;
    origin_timestamp: string;
    origin_quality: SnapshotQuality;
    origin_provenance: TwinProvenance[];
    parent_scenario_id?: string | null;
    evidence_ids: string[];
    seed: number;
    physiology_version: string;
    distribution_config_version: string;
    prior_version: string;
    created_at: string;
    assumptions: string[];
  };
  warnings: string[];
  safety_disclaimer: string;
  representative_sample_ids: { low: string; median: string; high: string };
}
