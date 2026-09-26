import type { ScenarioResult } from "@/lib/twin/scenario/types";
import type { ScenarioTraceStep } from "@/lib/twin/scenario/trace";

export function scenarioReport(result: ScenarioResult, trace: readonly ScenarioTraceStep[]): string {
  const lines = [
    "BeatIT hypothetical simulation",
    `Origin snapshot: ${result.definition.origin.snapshotId} (${result.definition.origin.timestamp})`,
    "",
    ...trace.filter((step) => step.delta !== null && Math.abs(step.delta) > 1e-9).map((step) => {
      const sign = step.delta! >= 0 ? "+" : "";
      return `${step.nodeId}: ${step.baseline} → ${step.scenario} ${step.unit ?? ""} (${sign}${step.delta!.toFixed(2)})`;
    }),
    "",
    "This is a deterministic, bounded educational counterfactual. It is not a diagnosis or treatment recommendation.",
  ];
  return lines.join("\n");
}
