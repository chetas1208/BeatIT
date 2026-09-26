import type { ShadowTrialMetricId } from "@/types/shadow-trial";

/** M6 scalar metrics that have an explicitly supported hemodynamic display. */
export type HemodynamicMetricId = Extract<
  ShadowTrialMetricId,
  "stroke_volume_ml" | "cardiac_output_l_min" | "map_mmhg"
>;

export type HemodynamicDisplayDomain = "volume" | "flow" | "pressure";
export type HemodynamicDirection = "increase" | "decrease" | "neutral" | "unavailable";

export interface HemodynamicDisplayInput {
  readonly metricId: HemodynamicMetricId;
  /** M6 paired baseline value; null means the value was not supplied. */
  readonly baseline: number | null;
  /** M6 paired scenario value; null means the value was not supplied. */
  readonly scenario: number | null;
  /** Canonical M6 scenario-minus-baseline delta. It is never recomputed here. */
  readonly delta: number | null;
  /** Optional source unit assertion. The display always uses the M6 unit policy. */
  readonly unit?: string | null;
}

export interface HemodynamicDisplayValue {
  readonly metricId: HemodynamicMetricId;
  readonly label: string;
  readonly domain: HemodynamicDisplayDomain;
  readonly baseline: number | null;
  readonly scenario: number | null;
  readonly delta: number | null;
  readonly unit: string;
  readonly deltaUnit: string;
  readonly direction: HemodynamicDirection;
  /** Numerical movement only; this label makes no clinical desirability claim. */
  readonly directionLabel: "Increase" | "Decrease" | "Neutral" | "Unavailable";
  readonly valueAvailability: "complete" | "partial" | "unavailable";
}

interface HemodynamicPolicy {
  readonly label: string;
  readonly domain: HemodynamicDisplayDomain;
  readonly unit: string;
  readonly neutralTolerance: number;
}

export const M6_HEMODYNAMIC_METRIC_ORDER: readonly HemodynamicMetricId[] = [
  "stroke_volume_ml",
  "cardiac_output_l_min",
  "map_mmhg",
];

export const M6_HEMODYNAMIC_POLICIES: Readonly<Record<HemodynamicMetricId, HemodynamicPolicy>> = {
  stroke_volume_ml: {
    label: "Stroke volume",
    domain: "volume",
    unit: "mL",
    neutralTolerance: 0.01,
  },
  cardiac_output_l_min: {
    label: "Cardiac output",
    domain: "flow",
    unit: "L/min",
    neutralTolerance: 0.001,
  },
  map_mmhg: {
    label: "Mean arterial pressure",
    domain: "pressure",
    unit: "mmHg",
    neutralTolerance: 0.01,
  },
};

function policyFor(metricId: HemodynamicMetricId): HemodynamicPolicy {
  const policy = M6_HEMODYNAMIC_POLICIES[metricId];
  if (!policy) throw new RangeError(`Unsupported M6 hemodynamic metric: ${String(metricId)}`);
  return policy;
}

function finiteOrNull(value: number | null, field: string): number | null {
  if (value === null) return null;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new RangeError(`${field} must be finite or null`);
  }
  return value;
}

function availabilityFor(baseline: number | null, scenario: number | null, delta: number | null): HemodynamicDisplayValue["valueAvailability"] {
  const present = [baseline, scenario, delta].filter((value) => value !== null).length;
  return present === 3 ? "complete" : present === 0 ? "unavailable" : "partial";
}

function directionFor(delta: number | null, neutralTolerance: number): HemodynamicDirection {
  if (delta === null) return "unavailable";
  if (Math.abs(delta) <= neutralTolerance) return "neutral";
  return delta > 0 ? "increase" : "decrease";
}

function directionLabelFor(direction: HemodynamicDirection): HemodynamicDisplayValue["directionLabel"] {
  switch (direction) {
    case "increase":
      return "Increase";
    case "decrease":
      return "Decrease";
    case "neutral":
      return "Neutral";
    default:
      return "Unavailable";
  }
}

/**
 * Map one already-computed M6 scalar into a display-ready value.
 *
 * Baseline, scenario, and delta are copied as supplied. In particular, this
 * function does not derive a delta from the two values or infer any clinical
 * meaning from its sign.
 */
export function mapHemodynamicDisplayValue(input: HemodynamicDisplayInput): HemodynamicDisplayValue {
  const policy = policyFor(input.metricId);
  const baseline = finiteOrNull(input.baseline, "baseline");
  const scenario = finiteOrNull(input.scenario, "scenario");
  const delta = finiteOrNull(input.delta, "delta");
  if (input.unit !== undefined && input.unit !== null && input.unit !== policy.unit) {
    throw new RangeError(`Unit for ${input.metricId} does not match ${policy.unit}`);
  }

  const direction = directionFor(delta, policy.neutralTolerance);
  return {
    metricId: input.metricId,
    label: policy.label,
    domain: policy.domain,
    baseline,
    scenario,
    delta,
    unit: policy.unit,
    deltaUnit: policy.unit,
    direction,
    directionLabel: directionLabelFor(direction),
    valueAvailability: availabilityFor(baseline, scenario, delta),
  };
}

/** Map supported M6 SV/CO/MAP values in stable display order. */
export function mapHemodynamicDisplayValues(
  inputs: readonly HemodynamicDisplayInput[],
): readonly HemodynamicDisplayValue[] {
  const byMetric = new Map(inputs.map((input) => [input.metricId, input]));
  return M6_HEMODYNAMIC_METRIC_ORDER.flatMap((metricId) => {
    const input = byMetric.get(metricId);
    return input ? [mapHemodynamicDisplayValue(input)] : [];
  });
}

