import type { ScenarioResult } from "@/lib/twin/scenario/types";

export interface ScenarioHistory {
  readonly past: readonly ScenarioResult[];
  readonly present: ScenarioResult | null;
  readonly future: readonly ScenarioResult[];
}

export function createScenarioHistory(initial: ScenarioResult | null = null): ScenarioHistory {
  return { past: [], present: initial, future: [] };
}

export function pushScenario(history: ScenarioHistory, next: ScenarioResult): ScenarioHistory {
  return {
    past: history.present ? [...history.past, history.present] : history.past,
    present: next,
    future: [],
  };
}

export function undoScenario(history: ScenarioHistory): ScenarioHistory {
  const previous = history.past.at(-1);
  if (!previous || !history.present) return history;
  return { past: history.past.slice(0, -1), present: previous, future: [history.present, ...history.future] };
}

export function redoScenario(history: ScenarioHistory): ScenarioHistory {
  const next = history.future[0];
  if (!next || !history.present) return history;
  return { past: [...history.past, history.present], present: next, future: history.future.slice(1) };
}

export function resetScenario(history?: ScenarioHistory): ScenarioHistory {
  void history;
  return { past: [], present: null, future: [] };
}
