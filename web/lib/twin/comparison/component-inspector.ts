/**
 * Pure view model for one semantic component in a valid M6 paired result.
 *
 * The values and delta are supplied by the canonical pair. This module only
 * validates and arranges them for presentation; it never derives physiology.
 */

export interface CanonicalInspectorValue {
  readonly value: number | null;
  readonly unit: string;
}

export interface CanonicalInspectorDelta {
  readonly value: number | null;
  readonly unit: string;
}

export interface PairedCanonicalValues {
  readonly baseline: CanonicalInspectorValue;
  readonly scenario: CanonicalInspectorValue;
  /** Scenario-minus-baseline delta supplied by the paired result. */
  readonly delta: CanonicalInspectorDelta;
}

export interface ComponentInspectorInput {
  readonly componentId: string;
  readonly componentLabel?: string | null;
  readonly metricId: string;
  readonly metricLabel?: string | null;
  readonly values: PairedCanonicalValues;
  /** Causal language must be supplied by the deterministic comparison layer. */
  readonly causalText?: string | null;
  /** Provenance language must identify the source of the paired values. */
  readonly provenanceText?: string | null;
  readonly limitations?: readonly string[];
}

export type ComponentInspectorAvailability = "complete" | "partial" | "unavailable";

export interface ComponentInspectorModel {
  readonly componentId: string;
  readonly componentLabel: string;
  readonly metricId: string;
  readonly metricLabel: string;
  readonly baseline: CanonicalInspectorValue;
  readonly scenario: CanonicalInspectorValue;
  readonly delta: CanonicalInspectorDelta;
  readonly availability: ComponentInspectorAvailability;
  readonly causalText: string;
  readonly provenanceText: string;
  readonly limitations: readonly string[];
}

const DEFAULT_CAUSAL_TEXT = "No causal explanation is available for this comparison.";
const DEFAULT_PROVENANCE_TEXT = "No provenance description is available for this comparison.";
const DEFAULT_LIMITATION =
  "Values are read from the canonical paired result; this inspector does not recompute physiology.";

function requireText(value: string, field: string): string {
  const normalized = value.trim();
  if (!normalized) throw new RangeError(`${field} must not be empty`);
  return normalized;
}

function optionalText(value: string | null | undefined, fallback: string): string {
  const normalized = value?.trim();
  return normalized || fallback;
}

function validateValue(value: CanonicalInspectorValue | CanonicalInspectorDelta, field: string): void {
  requireText(value.unit, `${field}.unit`);
  if (value.value !== null && (!Number.isFinite(value.value) || typeof value.value !== "number")) {
    throw new RangeError(`${field}.value must be finite or null`);
  }
}

function availabilityFor(values: PairedCanonicalValues): ComponentInspectorAvailability {
  const present = [values.baseline.value, values.scenario.value, values.delta.value]
    .filter((value) => value !== null).length;
  if (present === 3) return "complete";
  if (present === 0) return "unavailable";
  return "partial";
}

function uniqueLimitations(limitations: readonly string[] | undefined): readonly string[] {
  const normalized = (limitations ?? [])
    .map((limitation) => limitation.trim())
    .filter(Boolean);
  return [...new Set([DEFAULT_LIMITATION, ...normalized])];
}

/**
 * Build a deterministic, immutable-ready inspector model from paired values.
 * Numeric fields are copied exactly from the input, including nulls and zero.
 */
export function buildComponentInspectorModel(input: ComponentInspectorInput): ComponentInspectorModel {
  const componentId = requireText(input.componentId, "componentId");
  const metricId = requireText(input.metricId, "metricId");
  const componentLabel = optionalText(input.componentLabel, componentId.replaceAll("-", " "));
  const metricLabel = optionalText(input.metricLabel, metricId.replaceAll("_", " "));

  validateValue(input.values.baseline, "baseline");
  validateValue(input.values.scenario, "scenario");
  validateValue(input.values.delta, "delta");
  if (input.values.baseline.unit !== input.values.scenario.unit) {
    throw new RangeError("baseline and scenario units must match");
  }

  return {
    componentId,
    componentLabel,
    metricId,
    metricLabel,
    baseline: { ...input.values.baseline },
    scenario: { ...input.values.scenario },
    delta: { ...input.values.delta },
    availability: availabilityFor(input.values),
    causalText: optionalText(input.causalText, DEFAULT_CAUSAL_TEXT),
    provenanceText: optionalText(input.provenanceText, DEFAULT_PROVENANCE_TEXT),
    limitations: uniqueLimitations(input.limitations),
  };
}

