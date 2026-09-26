/**
 * Bounded display mapping for the contraction layer of the M7 paired view.
 *
 * The paired scalar values and delta are authoritative inputs. This module
 * only turns them into renderer-friendly display levels and conservative
 * labels; it does not derive physiology or claim biomechanical precision.
 */

export type ContractionMetricId = "ejection_fraction_pct" | "contractility_index";

export type ContractionVisualAvailability = "complete" | "partial" | "unavailable";

export type ContractionVisualDirection =
  | "higher_supplied_value"
  | "lower_supplied_value"
  | "no_modeled_difference"
  | "value_unavailable";

export const CONTRACTION_VISUAL_LIMITATION =
  "This is a bounded visualization of supplied paired scalar values, not a biomechanical or finite-element mechanics model.";
export const CONTRACTION_DISPLAY_LIMITATION =
  "Display levels and emphasis are presentation transforms; they are not physical contraction measurements.";
export const CONTRACTION_MISSING_LIMITATION =
  "Missing or unsupported values are left unavailable and are not inferred from other cardiac fields.";
export const CONTRACTION_RANGE_LIMITATION =
  "Values outside the display range are clamped for presentation and are not reinterpreted as physiology.";

const DISPLAY_MAXIMUM: Readonly<Record<ContractionMetricId, number>> = {
  ejection_fraction_pct: 100,
  contractility_index: 1.5,
};

const METRIC_LABEL: Readonly<Record<ContractionMetricId, string>> = {
  ejection_fraction_pct: "Ejection fraction",
  contractility_index: "Contractility index",
};

const ACCEPTED_VALUE_UNITS: Readonly<Record<ContractionMetricId, readonly string[]>> = {
  ejection_fraction_pct: ["%", "percentage_points"],
  contractility_index: ["index"],
};

const ACCEPTED_DELTA_UNITS: Readonly<Record<ContractionMetricId, readonly string[]>> = {
  ejection_fraction_pct: ["%", "percentage_points"],
  contractility_index: ["index"],
};

export interface CanonicalContractionValue {
  readonly value: number | null;
  readonly unit: string;
}

export interface ContractionPairInput {
  readonly metricId: ContractionMetricId;
  readonly baseline: CanonicalContractionValue;
  readonly scenario: CanonicalContractionValue;
  /** Scenario-minus-baseline delta supplied by the canonical paired result. */
  readonly delta: CanonicalContractionValue;
}

export interface ContractionVisualSide {
  readonly label: "BASELINE VISUAL REFERENCE" | "SCENARIO VISUAL REFERENCE";
  readonly value: number | null;
  readonly unit: string;
  /** A bounded display level only; null means that side cannot be mapped. */
  readonly displayLevel: number | null;
}

export interface ContractionVisualDifference {
  readonly delta: number | null;
  readonly unit: string;
  readonly direction: ContractionVisualDirection;
  readonly label:
    | "SUPPLIED VALUE HIGHER"
    | "SUPPLIED VALUE LOWER"
    | "NO MODELED DIFFERENCE"
    | "VALUE UNAVAILABLE";
  /** Bounded emphasis derived from the supplied delta for display only. */
  readonly displayEmphasis: number;
}

export interface ContractionVisualMapping {
  readonly metricId: ContractionMetricId;
  readonly metricLabel: string;
  readonly baseline: ContractionVisualSide;
  readonly scenario: ContractionVisualSide;
  readonly difference: ContractionVisualDifference;
  readonly availability: ContractionVisualAvailability;
  readonly limitations: readonly string[];
}

function assertMetricId(metricId: ContractionMetricId): void {
  if (metricId !== "ejection_fraction_pct" && metricId !== "contractility_index") {
    throw new RangeError(`Unsupported contraction metric: ${String(metricId)}`);
  }
}

function assertUnit(value: CanonicalContractionValue, field: string): string {
  if (typeof value.unit !== "string" || value.unit.trim() === "") {
    throw new RangeError(`${field}.unit must not be empty`);
  }
  return value.unit.trim();
}

function assertValue(value: CanonicalContractionValue, field: string): void {
  if (value.value !== null && (typeof value.value !== "number" || !Number.isFinite(value.value))) {
    throw new RangeError(`${field}.value must be finite or null`);
  }
}

function assertMetricUnits(
  metricId: ContractionMetricId,
  baselineUnit: string,
  scenarioUnit: string,
  deltaUnit: string,
): void {
  if (!ACCEPTED_VALUE_UNITS[metricId].includes(baselineUnit) || !ACCEPTED_VALUE_UNITS[metricId].includes(scenarioUnit)) {
    throw new RangeError(`${metricId} baseline and scenario units are not supported`);
  }
  if (!ACCEPTED_DELTA_UNITS[metricId].includes(deltaUnit)) {
    throw new RangeError(`${metricId} delta unit is not supported`);
  }
}

function availabilityFor(input: ContractionPairInput): ContractionVisualAvailability {
  const present = [input.baseline.value, input.scenario.value, input.delta.value]
    .filter((value) => value !== null).length;
  if (present === 3) return "complete";
  if (present === 0) return "unavailable";
  return "partial";
}

function boundedLevel(value: number | null, maximum: number): number | null {
  if (value === null) return null;
  return Math.min(1, Math.max(0, value / maximum));
}

function differenceFor(
  delta: CanonicalContractionValue,
  displayMaximum: number,
): ContractionVisualDifference {
  if (delta.value === null) {
    return {
      delta: null,
      unit: delta.unit,
      direction: "value_unavailable",
      label: "VALUE UNAVAILABLE",
      displayEmphasis: 0,
    };
  }

  if (delta.value === 0) {
    return {
      delta: 0,
      unit: delta.unit,
      direction: "no_modeled_difference",
      label: "NO MODELED DIFFERENCE",
      displayEmphasis: 0,
    };
  }

  return {
    delta: delta.value,
    unit: delta.unit,
    direction: delta.value > 0 ? "higher_supplied_value" : "lower_supplied_value",
    label: delta.value > 0 ? "SUPPLIED VALUE HIGHER" : "SUPPLIED VALUE LOWER",
    displayEmphasis: Math.min(1, Math.abs(delta.value) / displayMaximum),
  };
}

/**
 * Build a renderer-neutral contraction difference mapping.
 *
 * `delta` is copied from the paired result and is never recomputed from the
 * two side values. A display level is a bounded visual coordinate, not a
 * claim about shortening, force, tissue mechanics, or clinical function.
 */
export function buildContractionVisualMapping(
  input: ContractionPairInput,
): ContractionVisualMapping {
  assertMetricId(input.metricId);
  const baselineUnit = assertUnit(input.baseline, "baseline");
  const scenarioUnit = assertUnit(input.scenario, "scenario");
  const deltaUnit = assertUnit(input.delta, "delta");
  assertValue(input.baseline, "baseline");
  assertValue(input.scenario, "scenario");
  assertValue(input.delta, "delta");

  if (baselineUnit !== scenarioUnit) {
    throw new RangeError("baseline and scenario contraction units must match");
  }
  assertMetricUnits(input.metricId, baselineUnit, scenarioUnit, deltaUnit);

  const displayMaximum = DISPLAY_MAXIMUM[input.metricId];
  return {
    metricId: input.metricId,
    metricLabel: METRIC_LABEL[input.metricId],
    baseline: {
      label: "BASELINE VISUAL REFERENCE",
      value: input.baseline.value,
      unit: baselineUnit,
      displayLevel: boundedLevel(input.baseline.value, displayMaximum),
    },
    scenario: {
      label: "SCENARIO VISUAL REFERENCE",
      value: input.scenario.value,
      unit: scenarioUnit,
      displayLevel: boundedLevel(input.scenario.value, displayMaximum),
    },
    difference: differenceFor({ value: input.delta.value, unit: deltaUnit }, displayMaximum),
    availability: availabilityFor(input),
    limitations: [
      CONTRACTION_VISUAL_LIMITATION,
      CONTRACTION_DISPLAY_LIMITATION,
      CONTRACTION_MISSING_LIMITATION,
      CONTRACTION_RANGE_LIMITATION,
    ],
  };
}
