import type { HeartComponentVisualState } from "@/lib/heart/registry";

export type SemanticVisualStatus = "available" | "unavailable" | "uncertain" | "finding";

export type SemanticDifference = {
  /** Future baseline/scenario values. They remain optional until difference mode is wired. */
  baseline?: number;
  scenario?: number;
  delta?: number;
  magnitude?: number;
};

export interface SemanticVisualState extends HeartComponentVisualState {
  status: SemanticVisualStatus;
  available: boolean;
  uncertain: boolean;
  hasFinding: boolean;
  difference: SemanticDifference | null;
}

export interface SemanticVisualStateInput {
  selected: boolean;
  hovered: boolean;
  hasFinding: boolean;
  available: boolean;
  /** True when the available evidence is explicitly uncertain. */
  uncertain?: boolean;
  confidence?: number;
  findingSeverity?: number;
  /** Reserved for the future baseline-versus-scenario visual mode. */
  difference?: SemanticDifference | null;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function statusFor({ available, uncertain, hasFinding }: SemanticVisualStateInput): SemanticVisualStatus {
  if (!available) return "unavailable";
  if (uncertain) return "uncertain";
  if (hasFinding) return "finding";
  return "available";
}

/**
 * Maps patient-data semantics to renderer-neutral visual values.
 * Missing data is deliberately dimmed, not treated as a normal finding.
 */
export function getSemanticVisualState(input: SemanticVisualStateInput): SemanticVisualState {
  const { selected, hovered, hasFinding, available, uncertain = false } = input;
  const status = statusFor(input);
  const findingSeverity = input.findingSeverity === undefined
    ? undefined
    : clamp(input.findingSeverity, 0, 1);
  const confidence = input.confidence === undefined
    ? undefined
    : clamp(input.confidence, 0, 1);

  const emphasis = selected
    ? 1
    : hovered
      ? 0.65
      : hasFinding
        ? 0.35 + (findingSeverity ?? 0) * 0.25
        : uncertain
          ? 0.18
          : 0;

  return {
    visible: true,
    hovered,
    selected,
    focused: selected,
    opacity: selected ? 1 : hovered ? 0.92 : available ? (uncertain ? 0.64 : 0.78) : 0.42,
    emphasis: clamp(emphasis, 0, 1),
    ...(confidence === undefined ? {} : { confidence }),
    ...(findingSeverity === undefined ? {} : { findingSeverity }),
    ...(input.difference?.magnitude === undefined ? {} : { differenceMagnitude: input.difference.magnitude }),
    status,
    available,
    uncertain,
    hasFinding,
    difference: input.difference ?? null,
  };
}

export function isUnavailable(state: Pick<SemanticVisualState, "status">): boolean {
  return state.status === "unavailable";
}

export function hasVisualFinding(state: Pick<SemanticVisualState, "status">): boolean {
  return state.status === "finding";
}

export function hasVisualDifference(state: Pick<SemanticVisualState, "difference">): boolean {
  return state.difference !== null;
}
