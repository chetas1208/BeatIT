import type { CausalPropagationResult } from "@/lib/twin/scenario/causal";

export interface ScenarioTraceStep {
  readonly nodeId: string;
  readonly label: string;
  readonly baseline: number | null;
  readonly scenario: number | null;
  readonly delta: number | null;
  readonly unit?: string | null;
  readonly percentage: number | null;
}

export function traceFromPropagation(propagation: CausalPropagationResult): readonly ScenarioTraceStep[] {
  const labels = new Map(propagation.sources.map((source) => [source.id, source.label]));
  return propagation.deltas.map((delta) => ({
    nodeId: delta.nodeId,
    label: labels.get(delta.sourceIds[0] ?? "") ?? delta.variable,
    baseline: delta.baseline,
    scenario: delta.scenario,
    delta: delta.delta,
    unit: delta.unit,
    percentage: delta.baseline == null || delta.baseline === 0 || delta.delta == null
      ? null
      : (delta.delta / Math.abs(delta.baseline)) * 100,
  }));
}
