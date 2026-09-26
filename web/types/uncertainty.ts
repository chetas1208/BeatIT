import type { MissingValuePolicy } from "@/types/heart";

export type UncertaintyKind = "measurement" | "parameter" | "population_model_prior" | "missing_evidence" | "simulation_output";
export type UncertaintyNature = "aleatoric" | "epistemic" | "mixed" | "unknown";
export type UncertaintyAssessment = "quantified" | "qualitative" | "unquantified";

export interface NumericInterval {
  readonly lower: number;
  readonly upper: number;
  readonly unit: string;
  readonly coverageProbability?: number | null;
}

export type NumericDistribution =
  | { readonly family: "normal"; readonly standardDeviation: number }
  | { readonly family: "uniform" }
  | { readonly family: "empirical"; readonly quantiles: readonly { probability: number; value: number }[] }
  | { readonly family: "unknown" };

export interface UncertaintyReferences {
  readonly sourceMapFields?: readonly string[];
  readonly sourceFileIds?: readonly string[];
  readonly evidenceIds?: readonly string[];
}

export interface UncertaintyRecordBase {
  readonly id: string;
  readonly kind: UncertaintyKind;
  readonly nature: UncertaintyNature;
  readonly assessment: UncertaintyAssessment;
  readonly affectedPaths: readonly string[];
  readonly references?: UncertaintyReferences | null;
  readonly note?: string | null;
}

export interface MeasurementUncertaintyRecord extends UncertaintyRecordBase {
  readonly kind: "measurement";
  readonly quantityPath: string;
  readonly estimate: number;
  readonly unit: string;
  readonly interval?: NumericInterval | null;
  readonly standardUncertainty?: number | null;
  readonly distribution?: NumericDistribution | null;
  readonly method?: string | null;
}

export interface ParameterUncertaintyRecord extends UncertaintyRecordBase {
  readonly kind: "parameter";
  readonly parameterPath: string;
  readonly nominalValue: number;
  readonly unit: string;
  readonly interval?: NumericInterval | null;
  readonly distribution?: NumericDistribution | null;
}

export interface PopulationModelPriorUncertaintyRecord extends UncertaintyRecordBase {
  readonly kind: "population_model_prior";
  readonly fieldPath: string;
  readonly priorValue: number;
  readonly unit: string;
  readonly priorConfidence?: number | null;
  readonly method?: string | null;
  readonly evidence?: string | null;
}

export interface MissingEvidenceUncertaintyRecord extends UncertaintyRecordBase {
  readonly kind: "missing_evidence";
  readonly missingFields: readonly string[];
  readonly missingCriticalFields?: readonly string[];
  readonly policy?: MissingValuePolicy | null;
}

export interface SimulationOutputUncertaintyRecord extends UncertaintyRecordBase {
  readonly kind: "simulation_output";
  readonly outputPath: string;
  readonly centralValue?: number | null;
  readonly interval: NumericInterval;
  readonly scenarioId?: string | null;
  readonly simulationLabel?: string | null;
}

export type UncertaintyRecord = MeasurementUncertaintyRecord | ParameterUncertaintyRecord | PopulationModelPriorUncertaintyRecord | MissingEvidenceUncertaintyRecord | SimulationOutputUncertaintyRecord;

export interface UncertaintySummary {
  readonly schemaVersion: 1;
  readonly records: readonly UncertaintyRecord[];
}
