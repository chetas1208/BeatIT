import { HeartComponentRegistry } from "@/lib/heart/registry";
import type { ComponentDelta } from "@/lib/twin/scenario/types";

export interface ScenarioComponentView {
  readonly componentId: string;
  readonly displayName: string;
  readonly category: string;
  readonly deltas: readonly ComponentDelta[];
}

export function componentViews(deltas: readonly ComponentDelta[]): readonly ScenarioComponentView[] {
  return Array.from(new Set(deltas.map((delta) => delta.componentId))).map((componentId) => {
    const definition = HeartComponentRegistry.getComponent(componentId);
    return {
      componentId,
      displayName: definition?.displayName ?? componentId,
      category: definition?.category ?? "functional",
      deltas: deltas.filter((delta) => delta.componentId === componentId),
    };
  });
}
