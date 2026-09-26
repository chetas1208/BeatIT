import { HeartComponentRegistry } from "@/lib/heart/registry";

/** Stable ID from the shared semantic heart-component registry. */
export type HeartComponentId = string;

export type ComparisonSide = "baseline" | "scenario";
export type ComparisonSelectionMode = "linked" | "unlinked";

export interface ComparisonSelectionState {
  readonly baselineComponentId: HeartComponentId | null;
  readonly scenarioComponentId: HeartComponentId | null;
}

export const EMPTY_COMPARISON_SELECTION: ComparisonSelectionState = Object.freeze({
  baselineComponentId: null,
  scenarioComponentId: null,
});

function assertComparisonSide(side: ComparisonSide): void {
  if (side !== "baseline" && side !== "scenario") {
    throw new RangeError(`Unsupported comparison side: ${String(side)}`);
  }
}

function assertSelectionMode(mode: ComparisonSelectionMode): void {
  if (mode !== "linked" && mode !== "unlinked") {
    throw new RangeError(`Unsupported comparison selection mode: ${String(mode)}`);
  }
}

function assertSelectableComponentId(componentId: HeartComponentId): void {
  if (typeof componentId !== "string" || componentId.length === 0) {
    throw new RangeError("Heart component ID must be a non-empty semantic ID");
  }

  const component = HeartComponentRegistry.getComponent(componentId);
  if (!component || !component.supportsSelection) {
    throw new RangeError(`Unknown or non-selectable heart component: ${componentId}`);
  }
}

/**
 * Resolve the counterpart through the shared semantic registry namespace.
 *
 * Both rendered hearts use the same component IDs. No mesh names or renderer
 * metadata are involved in comparison selection.
 */
export function counterpartComponentId(componentId: HeartComponentId): HeartComponentId {
  assertSelectableComponentId(componentId);
  return componentId;
}

/** Select the same registered semantic component in both heart instances. */
export function selectLinkedComponent(
  componentId: HeartComponentId,
): ComparisonSelectionState {
  const counterpartId = counterpartComponentId(componentId);
  return {
    baselineComponentId: componentId,
    scenarioComponentId: counterpartId,
  };
}

/** Select a registered semantic component only on the clicked side. */
export function selectUnlinkedComponent(
  state: ComparisonSelectionState,
  side: ComparisonSide,
  componentId: HeartComponentId,
): ComparisonSelectionState {
  assertComparisonSide(side);
  assertSelectableComponentId(componentId);

  if (side === "baseline") {
    return { ...state, baselineComponentId: componentId };
  }
  return { ...state, scenarioComponentId: componentId };
}

/** Apply linked or unlinked behavior to a semantic selection event. */
export function selectComparisonComponent(
  state: ComparisonSelectionState,
  side: ComparisonSide,
  componentId: HeartComponentId,
  mode: ComparisonSelectionMode,
): ComparisonSelectionState {
  assertComparisonSide(side);
  assertSelectionMode(mode);
  return mode === "linked"
    ? selectLinkedComponent(componentId)
    : selectUnlinkedComponent(state, side, componentId);
}

/** Clear one side, or both sides when the comparison is linked. */
export function clearComparisonSelection(
  state: ComparisonSelectionState,
  side: ComparisonSide,
  mode: ComparisonSelectionMode = "unlinked",
): ComparisonSelectionState {
  assertComparisonSide(side);
  assertSelectionMode(mode);

  if (mode === "linked") return { ...EMPTY_COMPARISON_SELECTION };

  return side === "baseline"
    ? { ...state, baselineComponentId: null }
    : { ...state, scenarioComponentId: null };
}
