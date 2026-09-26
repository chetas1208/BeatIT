/**
 * Provider-neutral contracts for the deterministic scenario causal graph.
 *
 * This module describes relationships and propagation evidence only. It does
 * not evaluate physiology, call a model provider, or contain presentation
 * concerns. Numeric propagation remains an explicit consumer of these types.
 */

export type CausalNodeId = string;
export type CausalEdgeId = string;
export type CausalPathId = string;
export type CausalSourceId = string;

export type CausalNodeKind =
  | "intervention"
  | "parameter"
  | "state"
  | "intermediate"
  | "observable"
  | "outcome";

export type CausalRelation =
  | "increases"
  | "decreases"
  | "modulates"
  | "constrains"
  | "derives";

/** The signed direction of an effect along an edge or path. */
export type CausalEffectSign = -1 | 0 | 1;

export type CausalSourceKind =
  | "measurement"
  | "clinical_evidence"
  | "deterministic_formula"
  | "assumption"
  | "derived_state"
  | "documentation";

/** A provenance reference for a graph relationship or propagated value. */
export interface CausalSource {
  readonly id: CausalSourceId;
  readonly kind: CausalSourceKind;
  readonly label: string;
  readonly reference?: string | null;
  readonly evidenceIds?: readonly string[];
  readonly method?: string | null;
  readonly confidence?: number | null;
  readonly note?: string | null;
}

/** A named physiological quantity or intervention in the causal graph. */
export interface CausalNode {
  readonly id: CausalNodeId;
  readonly label: string;
  readonly kind: CausalNodeKind;
  readonly variable: string;
  readonly unit?: string | null;
  readonly description?: string | null;
  readonly sourceIds: readonly CausalSourceId[];
}

/** A directed, signed relationship between two graph nodes. */
export interface CausalEdge {
  readonly id: CausalEdgeId;
  readonly from: CausalNodeId;
  readonly to: CausalNodeId;
  readonly relation: CausalRelation;
  readonly sign: CausalEffectSign;
  readonly sourceIds: readonly CausalSourceId[];
  readonly description?: string | null;
  readonly lagMs?: number | null;
}

/** The complete graph definition consumed by deterministic propagation. */
export interface CausalGraph {
  readonly id: string;
  readonly version: string;
  readonly nodes: readonly CausalNode[];
  readonly edges: readonly CausalEdge[];
  readonly sources: readonly CausalSource[];
}

/** A directed explanation path through the graph. */
export interface CausalPath {
  readonly id: CausalPathId;
  readonly from: CausalNodeId;
  readonly to: CausalNodeId;
  readonly nodeIds: readonly CausalNodeId[];
  readonly edgeIds: readonly CausalEdgeId[];
  readonly sign: CausalEffectSign;
  readonly sourceIds: readonly CausalSourceId[];
}

/** One deterministic value comparison produced during propagation. */
export interface CausalValueDelta {
  readonly nodeId: CausalNodeId;
  readonly variable: string;
  readonly unit?: string | null;
  readonly baseline: number | null;
  readonly scenario: number | null;
  readonly delta: number | null;
  readonly sourceIds: readonly CausalSourceId[];
}

export type CausalPropagationStatus = "complete" | "partial" | "blocked";

/**
 * Deterministic propagation output. `paths` and `deltas` are explicit so a
 * caller can render or audit the result without inferring causality from
 * numeric values alone.
 */
export interface CausalPropagationResult {
  readonly graphId: string;
  readonly graphVersion: string;
  readonly status: CausalPropagationStatus;
  readonly inputNodeIds: readonly CausalNodeId[];
  readonly affectedNodeIds: readonly CausalNodeId[];
  readonly deltas: readonly CausalValueDelta[];
  readonly paths: readonly CausalPath[];
  readonly sources: readonly CausalSource[];
  readonly warnings: readonly string[];
  readonly deterministic: true;
}
