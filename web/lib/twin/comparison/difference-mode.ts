/**
 * Renderer-neutral display policy for comparison difference mode.
 *
 * The numerical difference itself is supplied by the canonical paired-trial
 * layer. This module only decides how an already-computed difference should
 * be presented; it never derives cardiac values or changes orientation.
 */

export const DEFAULT_DIFFERENCE_EPSILON = 1e-6;
export const UNCHANGED_OPACITY = 0.28;
export const CHANGED_OPACITY = 1;
export const UNSUPPORTED_OPACITY = 0.52;
export const NO_MODELED_DIFFERENCE_TEXT = "NO MODELED DIFFERENCE";

export type DifferenceTreatment = "unchanged" | "changed" | "unsupported";

export interface DifferenceMetricInput {
  readonly absoluteDelta: number | null | undefined;
}

export interface DifferenceModeElement<TOrientation> {
  readonly componentId: string;
  readonly supported: boolean;
  readonly orientation: TOrientation;
  /** Canonical scenario-minus-baseline deltas; presentation does not recompute them. */
  readonly deltas?: readonly (number | null | undefined | DifferenceMetricInput)[];
  /** Convenience for a component with one canonical delta. */
  readonly delta?: number | null;
}

export interface DifferenceModeElementDisplay<TOrientation> {
  readonly componentId: string;
  readonly supported: boolean;
  readonly changed: boolean;
  readonly treatment: DifferenceTreatment;
  readonly opacity: number;
  readonly emphasis: number;
  /** The same orientation object supplied by the caller. No camera transform is applied. */
  readonly orientation: TOrientation;
  readonly magnitude: number | null;
}

export interface NoModeledDifferenceState {
  readonly kind: "no_modeled_difference";
  readonly text: typeof NO_MODELED_DIFFERENCE_TEXT;
}

export interface DifferenceModeResult<TOrientation> {
  readonly elements: readonly DifferenceModeElementDisplay<TOrientation>[];
  readonly hasModeledDifference: boolean;
  readonly emptyState: NoModeledDifferenceState | null;
}

function assertComponentId(componentId: string): void {
  if (typeof componentId !== "string" || componentId.trim().length === 0) {
    throw new RangeError("Difference-mode component ID must be a non-empty semantic ID");
  }
}

function assertEpsilon(epsilon: number): void {
  if (!Number.isFinite(epsilon) || epsilon < 0) {
    throw new RangeError("Difference-mode epsilon must be a finite non-negative number");
  }
}

function numericDelta(value: number | null | undefined | DifferenceMetricInput): number | null {
  const candidate = typeof value === "number" ? value : value?.absoluteDelta;
  return typeof candidate === "number" && Number.isFinite(candidate) ? candidate : null;
}

function finiteDeltas<TOrientation>(element: DifferenceModeElement<TOrientation>): readonly number[] {
  const values = [
    ...(element.delta === undefined ? [] : [element.delta]),
    ...(element.deltas ?? []),
  ];
  return values.flatMap((value) => {
    const delta = numericDelta(value);
    return delta === null ? [] : [delta];
  });
}

function displayFor<TOrientation>(
  element: DifferenceModeElement<TOrientation>,
  epsilon: number,
): DifferenceModeElementDisplay<TOrientation> {
  assertComponentId(element.componentId);
  const deltas = finiteDeltas(element);
  const magnitude = deltas.length === 0 ? null : Math.max(...deltas.map(Math.abs));
  const changed = element.supported && magnitude !== null && magnitude > epsilon;
  const treatment: DifferenceTreatment = !element.supported
    ? "unsupported"
    : changed
      ? "changed"
      : "unchanged";

  return {
    componentId: element.componentId,
    supported: element.supported,
    changed,
    treatment,
    opacity: treatment === "changed"
      ? CHANGED_OPACITY
      : treatment === "unsupported"
        ? UNSUPPORTED_OPACITY
        : UNCHANGED_OPACITY,
    emphasis: treatment === "changed" ? 1 : 0,
    orientation: element.orientation,
    magnitude,
  };
}

/**
 * Apply difference-only display semantics to semantic heart elements.
 *
 * Unsupported elements remain visible enough to preserve anatomical context,
 * while only supported, above-threshold deltas receive emphasis. Invalid or
 * missing deltas are never promoted to a visual difference.
 */
export function buildDifferenceMode<TOrientation>(
  elements: readonly DifferenceModeElement<TOrientation>[],
  options: { readonly epsilon?: number } = {},
): DifferenceModeResult<TOrientation> {
  const epsilon = options.epsilon ?? DEFAULT_DIFFERENCE_EPSILON;
  assertEpsilon(epsilon);
  const displays = elements.map((element) => displayFor(element, epsilon));
  const hasModeledDifference = displays.some((element) => element.changed);

  return {
    elements: displays,
    hasModeledDifference,
    emptyState: hasModeledDifference
      ? null
      : { kind: "no_modeled_difference", text: NO_MODELED_DIFFERENCE_TEXT },
  };
}

