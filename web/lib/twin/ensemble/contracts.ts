import type { CardiacTwinState } from "@/types/heart";
import type { ScenarioParameterKey } from "@/lib/twin/scenario/parameters";
import type { TwinProvenance, TwinSnapshot, TwinTimestamp } from "@/lib/twin/time/contracts";

export type DistributionFamily = "fixed" | "normal" | "lognormal" | "uniform" | "empirical";
export type DistributionSource = "measurement" | "derived" | "population_prior" | "expert_prior" | "scenario";

export interface DistributionBounds {
  readonly min: number;
  readonly max: number;
}

export interface ParameterDistribution {
  readonly parameterId: ScenarioParameterKey;
  readonly family: DistributionFamily;
  /** Family-specific values. Supported keys are value, mean, sd, min, max, and values. */
  readonly parameters: Readonly<Record<string, number | readonly number[]>>;
  readonly bounds: DistributionBounds;
  readonly source: DistributionSource;
  /** Original evidence source when the parameter was measured or derived. */
  readonly sourceDetail?: string;
  readonly evidenceIds: readonly string[];
  readonly rationale: string;
  readonly version: string;
}

export interface TwinSample {
  readonly id: string;
  readonly index: number;
  readonly seed: number;
  readonly originSnapshotId: string;
  readonly originQuality?: "observed" | "derived" | "interpolated" | "synthetic";
  readonly parameters: Readonly<Record<ScenarioParameterKey, number>>;
  readonly state: CardiacTwinState;
  readonly valid: boolean;
  readonly rejectionReasons: readonly string[];
}

export interface OutputDistribution {
  readonly metricId: string;
  readonly unit: string;
  readonly samples: readonly number[];
  readonly mean: number;
  readonly median: number;
  readonly variance: number;
  readonly standardDeviation: number;
  readonly quantiles: {
    readonly q05: number;
    readonly q25: number;
    readonly q75: number;
    readonly q95: number;
  };
  readonly min: number;
  readonly max: number;
}

export interface EnsembleProvenance {
  readonly originSnapshotId: string;
  readonly originTimestamp: TwinTimestamp;
  readonly originQuality: "observed" | "derived" | "interpolated" | "synthetic";
  readonly originProvenance: readonly TwinProvenance[];
  readonly parentScenarioId?: string;
  readonly evidenceIds: readonly string[];
  readonly seed: number;
  readonly physiologyVersion: string;
  readonly distributionConfigVersion: string;
  readonly priorVersion: string;
  readonly createdAt: TwinTimestamp;
  readonly assumptions: readonly string[];
}

export interface TwinEnsemble {
  readonly id: string;
  readonly originSnapshotId: string;
  readonly seed: number;
  readonly requestedSampleCount: number;
  readonly acceptedSampleCount: number;
  readonly rejectedSampleCount: number;
  readonly samples: readonly TwinSample[];
  readonly distributions: readonly OutputDistribution[];
  readonly parameterDistributions: readonly ParameterDistribution[];
  readonly provenance: EnsembleProvenance;
  readonly warnings: readonly string[];
  readonly safetyDisclaimer?: string;
  readonly representativeIds?: Readonly<Record<"low" | "median" | "high", string | null>>;
}

export interface EnsembleConfig {
  readonly seed: number;
  readonly requestedSampleCount: number;
  readonly distributions: readonly ParameterDistribution[];
  readonly physiologyVersion?: string;
  readonly distributionConfigVersion?: string;
  readonly priorVersion?: string;
  readonly parentScenarioId?: string;
}

export interface EnsembleRepresentatives {
  readonly median: TwinSample | null;
  readonly low: TwinSample | null;
  readonly high: TwinSample | null;
}

export type EnsembleMetricId = "ejection_fraction_pct" | "stroke_volume_ml" | "cardiac_output_l_min" | "heart_rate_bpm";

export interface EnsembleInput {
  readonly snapshot: TwinSnapshot;
  readonly config: EnsembleConfig;
}
