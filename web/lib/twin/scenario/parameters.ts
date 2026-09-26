import type { ScenarioParameterChange } from "@/lib/twin/scenario/types";

/** Names of the deterministic inputs that may be changed in a scenario. */
export type ScenarioParameterKey =
  | "heart_rate_bpm"
  | "preload_index"
  | "afterload_index"
  | "contractility_index"
  | "systemic_vascular_resistance_index";

export type ScenarioParameterUnit = "bpm" | "index";

export interface ScenarioParameterDefinition {
  readonly key: ScenarioParameterKey;
  readonly label: string;
  readonly unit: ScenarioParameterUnit;
  readonly min: number;
  readonly max: number;
  readonly defaultValue: number;
}

export type ScenarioParameterValues = {
  [Key in ScenarioParameterKey]: number;
};

export interface ScenarioParameterValidation {
  readonly valid: boolean;
  readonly errors: readonly string[];
}

export const SCENARIO_PARAMETER_DEFINITIONS: Readonly<
  Record<ScenarioParameterKey, ScenarioParameterDefinition>
> = Object.freeze({
  heart_rate_bpm: Object.freeze({
    key: "heart_rate_bpm",
    label: "Heart rate",
    unit: "bpm",
    min: 30,
    max: 200,
    defaultValue: 70,
  }),
  preload_index: Object.freeze({
    key: "preload_index",
    label: "Preload",
    unit: "index",
    min: 0,
    max: 1.5,
    defaultValue: 0.55,
  }),
  afterload_index: Object.freeze({
    key: "afterload_index",
    label: "Afterload",
    unit: "index",
    min: 0,
    max: 2,
    defaultValue: 0.5,
  }),
  contractility_index: Object.freeze({
    key: "contractility_index",
    label: "Contractility",
    unit: "index",
    min: 0,
    max: 1.5,
    defaultValue: 0.65,
  }),
  systemic_vascular_resistance_index: Object.freeze({
    key: "systemic_vascular_resistance_index",
    label: "Systemic vascular resistance (SVR)",
    unit: "index",
    min: 0,
    max: 2,
    defaultValue: 0.55,
  }),
});

export const SCENARIO_PARAMETER_KEYS: readonly ScenarioParameterKey[] =
  Object.freeze(Object.keys(SCENARIO_PARAMETER_DEFINITIONS) as ScenarioParameterKey[]);

export const DEFAULT_SCENARIO_PARAMETERS: Readonly<ScenarioParameterValues> =
  Object.freeze(
    Object.fromEntries(
      SCENARIO_PARAMETER_KEYS.map((key) => [
        key,
        SCENARIO_PARAMETER_DEFINITIONS[key].defaultValue,
      ]),
    ) as ScenarioParameterValues,
  );

function isParameterKey(value: string): value is ScenarioParameterKey {
  return Object.prototype.hasOwnProperty.call(SCENARIO_PARAMETER_DEFINITIONS, value);
}

/** Return the definition for a known parameter, or undefined for unknown input. */
export function getScenarioParameterDefinition(
  key: string,
): ScenarioParameterDefinition | undefined {
  return isParameterKey(key) ? SCENARIO_PARAMETER_DEFINITIONS[key] : undefined;
}

/** Check one value without coercing strings, NaN, or infinities. */
export function isValidScenarioParameter(key: string, value: unknown): value is number {
  const definition = getScenarioParameterDefinition(key);
  return (
    definition !== undefined &&
    typeof value === "number" &&
    Number.isFinite(value) &&
    value >= definition.min &&
    value <= definition.max
  );
}

/** Validate one parameter and return a concise error message when invalid. */
export function validateScenarioParameter(key: string, value: unknown): string | null {
  if (isValidScenarioParameter(key, value)) return null;
  const definition = getScenarioParameterDefinition(key);
  if (!definition) return `Unknown scenario parameter: ${key}`;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return `${key}: value must be a finite number`;
  }
  return `${key}: ${value} is outside bounds [${definition.min}, ${definition.max}]`;
}

/** Validate a partial set of scenario values without mutating the input. */
export function validateScenarioParameters(
  values: unknown,
): ScenarioParameterValidation {
  if (!values || typeof values !== "object" || Array.isArray(values)) {
    return { valid: false, errors: ["Scenario parameters must be an object"] };
  }

  const errors: string[] = [];
  for (const [key, value] of Object.entries(values)) {
    const error = validateScenarioParameter(key, value);
    if (error) errors.push(error);
  }

  return { valid: errors.length === 0, errors };
}

/** Return a fresh, mutable set of scenario values at the documented defaults. */
export function resetScenarioParameters(): ScenarioParameterValues {
  return { ...DEFAULT_SCENARIO_PARAMETERS };
}

/** Return the default value for one parameter. */
export function resetScenarioParameter(key: ScenarioParameterKey): number {
  return SCENARIO_PARAMETER_DEFINITIONS[key].defaultValue;
}

/** Build the existing scenario change contract after validating both endpoints. */
export function createScenarioParameterChange(
  parameter: ScenarioParameterKey,
  baseline: number,
  value: number,
): ScenarioParameterChange {
  const errors = [
    validateScenarioParameter(parameter, baseline),
    validateScenarioParameter(parameter, value),
  ].filter((error): error is string => error !== null);
  if (errors.length > 0) {
    throw new RangeError(errors.join("; "));
  }

  return {
    parameter,
    baseline,
    value,
    delta: value - baseline,
    unit: SCENARIO_PARAMETER_DEFINITIONS[parameter].unit,
  };
}
