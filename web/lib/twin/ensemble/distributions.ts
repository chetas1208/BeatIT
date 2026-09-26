import type { ScenarioParameterKey } from "@/lib/twin/scenario/parameters";
import { getScenarioParameterDefinition } from "@/lib/twin/scenario/parameters";
import type { DistributionBounds, ParameterDistribution } from "@/lib/twin/ensemble/contracts";

export interface RandomSource {
  next(): number;
}

/** Small deterministic PRNG. It is for reproducible simulation, not security. */
export function createSeededRandom(seed: number): RandomSource {
  if (!Number.isSafeInteger(seed)) throw new RangeError("Ensemble seed must be a safe integer");
  let state = (seed >>> 0) || 0x6d2b79f5;
  return {
    next() {
      state = Math.imul(state ^ (state >>> 15), state | 1);
      state ^= state + Math.imul(state ^ (state >>> 7), state | 61);
      return ((state ^ (state >>> 14)) >>> 0) / 4294967296;
    },
  };
}

function finite(value: unknown, name: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new RangeError(`${name} must be finite`);
  return value;
}

function numeric(parameters: Readonly<Record<string, number | readonly number[]>>, key: string): number {
  const value = parameters[key];
  if (typeof value !== "number") throw new RangeError(`Distribution parameter ${key} must be numeric`);
  return finite(value, `Distribution parameter ${key}`);
}

export function validateDistribution(distribution: ParameterDistribution): void {
  const definition = getScenarioParameterDefinition(distribution.parameterId);
  if (!definition) throw new RangeError(`Unknown ensemble parameter: ${distribution.parameterId}`);
  const bounds = distribution.bounds;
  finite(bounds.min, `${distribution.parameterId}.bounds.min`);
  finite(bounds.max, `${distribution.parameterId}.bounds.max`);
  if (bounds.min > bounds.max) throw new RangeError(`${distribution.parameterId}: bounds are reversed`);
  if (bounds.min < definition.min || bounds.max > definition.max) {
    throw new RangeError(`${distribution.parameterId}: bounds exceed scenario bounds`);
  }
  if (!distribution.rationale.trim() || !distribution.version.trim()) {
    throw new RangeError(`${distribution.parameterId}: rationale and version are required`);
  }
  if (distribution.evidenceIds.some((id) => !id.trim())) throw new RangeError(`${distribution.parameterId}: evidence IDs must be non-empty`);
  switch (distribution.family) {
    case "fixed": {
      const value = numeric(distribution.parameters, "value");
      if (value < bounds.min || value > bounds.max) throw new RangeError(`${distribution.parameterId}: fixed value outside bounds`);
      break;
    }
    case "normal":
    case "lognormal": {
      const mean = numeric(distribution.parameters, "mean");
      const sd = numeric(distribution.parameters, "sd");
      if (sd <= 0) throw new RangeError(`${distribution.parameterId}: standard deviation must be > 0`);
      if (distribution.family === "lognormal" && mean <= 0) throw new RangeError(`${distribution.parameterId}: lognormal mean must be > 0`);
      if (mean < bounds.min || mean > bounds.max) throw new RangeError(`${distribution.parameterId}: mean outside bounds`);
      break;
    }
    case "uniform": {
      const min = numeric(distribution.parameters, "min");
      const max = numeric(distribution.parameters, "max");
      if (min > max || min < bounds.min || max > bounds.max) throw new RangeError(`${distribution.parameterId}: invalid uniform range`);
      break;
    }
    case "empirical": {
      const values = distribution.parameters.values;
      if (!Array.isArray(values) || values.length === 0 || values.some((value) => typeof value !== "number" || !Number.isFinite(value))) {
        throw new RangeError(`${distribution.parameterId}: empirical values must be non-empty and finite`);
      }
      if (values.some((value) => value < bounds.min || value > bounds.max)) throw new RangeError(`${distribution.parameterId}: empirical value outside bounds`);
      break;
    }
    default:
      throw new RangeError(`Unsupported distribution family: ${distribution.family satisfies never}`);
  }
}

function normal(random: RandomSource): number {
  const u = Math.max(Number.MIN_VALUE, random.next());
  const v = Math.max(Number.MIN_VALUE, random.next());
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

export function sampleDistribution(distribution: ParameterDistribution, random: RandomSource): number {
  validateDistribution(distribution);
  const { parameters } = distribution;
  let value: number;
  switch (distribution.family) {
    case "fixed": value = numeric(parameters, "value"); break;
    case "normal": value = numeric(parameters, "mean") + numeric(parameters, "sd") * normal(random); break;
    case "lognormal": value = Math.exp(Math.log(numeric(parameters, "mean")) + numeric(parameters, "sd") * normal(random)); break;
    case "uniform": value = numeric(parameters, "min") + random.next() * (numeric(parameters, "max") - numeric(parameters, "min")); break;
    case "empirical": {
      const values = parameters.values;
      if (!Array.isArray(values)) throw new RangeError(`${distribution.parameterId}: empirical values missing`);
      value = values[Math.min(values.length - 1, Math.floor(random.next() * values.length))]!;
      break;
    }
    default: throw new RangeError(`Unsupported distribution family: ${distribution.family satisfies never}`);
  }
  // Values outside the declared support are rejected by the ensemble runner;
  // returning the raw draw preserves the rejection reason and avoids silent clamping.
  return value;
}

export function distributionBounds(parameterId: ScenarioParameterKey): DistributionBounds {
  const definition = getScenarioParameterDefinition(parameterId);
  if (!definition) throw new RangeError(`Unknown ensemble parameter: ${parameterId}`);
  return { min: definition.min, max: definition.max };
}

export function normalDistribution(
  parameterId: ScenarioParameterKey,
  mean: number,
  sd: number,
  source: ParameterDistribution["source"],
  evidenceIds: readonly string[],
  rationale: string,
  version = "m5-priors-v1",
): ParameterDistribution {
  return { parameterId, family: "normal", parameters: { mean, sd }, bounds: distributionBounds(parameterId), source, evidenceIds, rationale, version };
}
