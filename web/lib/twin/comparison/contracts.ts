import type { HeartSelectionState } from "@/lib/heart/contracts";
import type { CardiacTwinState, SimulationVisualization } from "@/types/heart";
import type { ShadowTrialPair, ShadowTrialScenarioDefinition } from "@/types/shadow-trial";

export type ComparisonClockMode = "phase_locked" | "physiologic_rate";

export interface ComparisonClockHeartRates {
  readonly baselineHeartRateBpm: number;
  readonly scenarioHeartRateBpm: number;
}

export interface ComparisonClockState extends ComparisonClockHeartRates {
  readonly mode: ComparisonClockMode;
  readonly playing: boolean;
  /** The shared visual cursor, normalized to the half-open interval [0, 1). */
  readonly normalizedPhase: number;
  readonly baselinePhase: number;
  readonly scenarioPhase: number;
  readonly playbackSpeed: number;
}

export interface CreateComparisonClockOptions {
  readonly mode?: ComparisonClockMode;
  readonly playing?: boolean;
  readonly normalizedPhase?: number;
  readonly playbackSpeed?: number;
}

export type ComparisonClockRateInput = ComparisonClockHeartRates;

export interface ComparisonClockStepOptions {
  /** Elapsed wall-clock time in milliseconds. */
  readonly elapsedMs: number;
}

/** Immutable commands corresponding to the operations exposed by clock.ts. */
export type ComparisonClockCommand =
  | { readonly type: "play" }
  | { readonly type: "pause" }
  | { readonly type: "reset" }
  | { readonly type: "seek"; readonly normalizedPhase: number }
  | { readonly type: "set_mode"; readonly mode: ComparisonClockMode }
  | { readonly type: "set_playback_speed"; readonly playbackSpeed: number }
  | { readonly type: "set_heart_rates"; readonly rates: ComparisonClockRateInput }
  | { readonly type: "resync" }
  | { readonly type: "advance"; readonly elapsedMs: number };

export type ComparisonClockCommandType = ComparisonClockCommand["type"];

export interface MetricDelta {
  metricId: string;
  baseline: number | null;
  counterfactual: number | null;
  absoluteDelta: number | null;
  relativeDelta: number | null;
  unit: string;
}

export interface ComponentComparison {
  componentId: string;
  baseline: number | null;
  counterfactual: number | null;
  deltas: readonly MetricDelta[];
  supported: boolean;
}

export interface ComparisonViewState {
  selectedPairId: string;
  selectedComponentId: string | null;
  linkedSelection: boolean;
  linkedCamera: boolean;
  differenceOnly: boolean;
  clockMode: ComparisonClockMode;
  playing: boolean;
  normalizedPhase: number;
}

export interface PairedHeartState {
  pairId: string;
  trialId: string;
  baselineSampleId: string;
  scenarioSampleId: string;
  baselineState: CardiacTwinState;
  scenarioState: CardiacTwinState;
  baselineVisualization: SimulationVisualization;
  scenarioVisualization: SimulationVisualization;
  scenarioDefinition: ShadowTrialScenarioDefinition | null;
  pair: ShadowTrialPair;
}

export interface HeartInstanceState {
  instanceId: "baseline" | "counterfactual";
  state: CardiacTwinState;
  visualization: SimulationVisualization;
  interaction: HeartSelectionState;
}
