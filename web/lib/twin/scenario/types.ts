import type { HeartComponentCategory } from "@/lib/heart/registry";
import type { CausalPropagationResult } from "@/lib/twin/scenario/causal";
import type { SnapshotQuality, TwinProvenance, TwinTimestamp } from "@/lib/twin/time/contracts";
import type { CardiacTwinState } from "@/types/heart";

/** A recursively immutable view of JSON-like domain data. */
export type ReadonlyDeep<T> = T extends (...args: never[]) => unknown
  ? T
  : T extends readonly (infer U)[]
    ? readonly ReadonlyDeep<U>[]
    : T extends object
      ? { readonly [K in keyof T]: ReadonlyDeep<T[K]> }
      : T;

/**
 * The observed snapshot from which a scenario was forked.
 *
 * This is deliberately a value object: scenario code may derive new states
 * from it, but it must never write hypothetical values back into the observed
 * timeline.
 */
export interface ObservedOriginMetadata {
  readonly snapshotId: string;
  readonly patientId: string;
  readonly timestamp: TwinTimestamp;
  readonly state: ReadonlyDeep<CardiacTwinState>;
  readonly provenance: readonly ReadonlyDeep<TwinProvenance>[];
  readonly evidenceIds: readonly string[];
  readonly quality?: SnapshotQuality;
}

/** Compatibility name for callers that refer to the fork origin directly. */
export type ObservedOrigin = ObservedOriginMetadata;

/** A bounded numeric manipulation supplied to a deterministic scenario engine. */
export interface ScenarioParameterChange {
  readonly parameter: string;
  readonly baseline: number;
  readonly value: number;
  readonly delta: number;
  readonly unit: string;
}

/** The user-visible, reproducible description of a counterfactual run. */
export interface ScenarioDefinition {
  readonly id: string;
  readonly label: string;
  readonly description?: string;
  readonly origin: ObservedOriginMetadata;
  readonly parameters: readonly ScenarioParameterChange[];
  readonly createdAt: TwinTimestamp;
}

/** A scenario state paired with its immutable observed origin. */
export interface ScenarioTwinState {
  readonly scenarioId: string;
  readonly origin: ObservedOriginMetadata;
  readonly state: ReadonlyDeep<CardiacTwinState>;
  readonly timestamp: TwinTimestamp;
  readonly provenance: readonly ReadonlyDeep<TwinProvenance>[];
}

export type ScenarioDeltaDirection = "increase" | "decrease" | "unchanged";

/** A baseline-to-scenario change for one semantic heart component. */
export interface ComponentDelta {
  readonly componentId: string;
  readonly componentCategory?: HeartComponentCategory;
  readonly metric: string;
  readonly baseline: number | null;
  readonly scenario: number | null;
  readonly delta: number | null;
  readonly unit?: string;
  readonly direction: ScenarioDeltaDirection;
  readonly provenance: readonly ReadonlyDeep<TwinProvenance>[];
}

/** Component-level comparison data exposed to the scenario inspector. */
export type ScenarioComponentDelta = ComponentDelta;

export type ScenarioStatus = "draft" | "computed" | "failed";

/** Complete deterministic output of one scenario evaluation. */
export interface ScenarioResult {
  readonly definition: ScenarioDefinition;
  readonly baseline: ObservedOriginMetadata;
  readonly scenario: ScenarioTwinState;
  readonly componentDeltas: readonly ComponentDelta[];
  readonly provenance: readonly ReadonlyDeep<TwinProvenance>[];
  readonly status: ScenarioStatus;
  readonly warnings: readonly string[];
  readonly computedAt: TwinTimestamp;
  readonly causal?: CausalPropagationResult;
}
