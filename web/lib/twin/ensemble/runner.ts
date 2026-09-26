import type { CardiacTwinState } from "@/types/heart";
import { baselineScenarioParameters, propagateScenario, type ScenarioInput } from "@/lib/twin/scenario/propagation";
import { getScenarioParameterDefinition } from "@/lib/twin/scenario/parameters";
import { createSeededRandom, sampleDistribution, validateDistribution } from "@/lib/twin/ensemble/distributions";
import { metricValue, summarizeDistribution } from "@/lib/twin/ensemble/statistics";
import type { EnsembleConfig, EnsembleMetricId, EnsembleRepresentatives, ParameterDistribution, TwinEnsemble, TwinSample } from "@/lib/twin/ensemble/contracts";
import type { TwinSnapshot } from "@/lib/twin/time/contracts";
import type { ScenarioDefinition } from "@/lib/twin/scenario/types";

const PHYSIOLOGY_VERSION = "m4-deterministic-v1";
const CONFIG_VERSION = "m5-ensemble-v1";
const PRIOR_VERSION = "m5-priors-v1";
const METRICS: readonly [EnsembleMetricId, string][] = [
  ["ejection_fraction_pct", "%"],
  ["stroke_volume_ml", "mL"],
  ["cardiac_output_l_min", "L/min"],
  ["heart_rate_bpm", "bpm"],
];

function stableSerialize(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value) ?? String(value);
  if (Array.isArray(value)) return `[${value.map(stableSerialize).join(",")}]`;
  const record = value as Record<string, unknown>;
  return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${stableSerialize(record[key])}`).join(",")}}`;
}

function hash(value: string): string {
  let result = 2166136261;
  for (const character of value) result = Math.imul(result ^ character.charCodeAt(0), 16777619);
  return (result >>> 0).toString(16).padStart(8, "0");
}

function numeric(value: { value: number } | null | undefined): number | null {
  return typeof value?.value === "number" && Number.isFinite(value.value) ? value.value : null;
}

function sampleParameters(snapshot: TwinSnapshot, distributions: readonly ParameterDistribution[], random: ReturnType<typeof createSeededRandom>): { values: Record<keyof ReturnType<typeof baselineScenarioParameters>, number>; reasons: string[] } {
  const values = {} as Record<keyof ReturnType<typeof baselineScenarioParameters>, number>;
  const reasons: string[] = [];
  for (const distribution of distributions) {
    const value = sampleDistribution(distribution, random);
    const definition = getScenarioParameterDefinition(distribution.parameterId);
    if (!definition || value < distribution.bounds.min || value > distribution.bounds.max) {
      reasons.push(`${distribution.parameterId}: sampled value ${value} outside declared bounds`);
      continue;
    }
    values[distribution.parameterId] = value;
  }
  for (const parameter of ["heart_rate_bpm", "preload_index", "afterload_index", "contractility_index", "systemic_vascular_resistance_index"] as const) {
    if (!(parameter in values)) reasons.push(`${parameter}: no valid distribution sample`);
  }
  return { values, reasons };
}

function validity(state: CardiacTwinState): string[] {
  const reasons: string[] = [];
  const edv = numeric(state.measurements.edv_ml);
  const esv = numeric(state.measurements.esv_ml);
  const ef = numeric(state.measurements.ejection_fraction_pct);
  const sv = numeric(state.measurements.stroke_volume_ml);
  const co = numeric(state.measurements.cardiac_output_l_min);
  if (edv == null || edv <= 0) reasons.push("EDV must be positive");
  if (esv == null || esv <= 0) reasons.push("ESV must be positive");
  if (edv != null && esv != null && edv <= esv) reasons.push("EDV must exceed ESV");
  if (ef == null || ef < 0 || ef > 100) reasons.push("EF must be within 0–100%");
  if (sv == null || sv <= 0) reasons.push("stroke volume must be positive");
  if (co == null || co <= 0) reasons.push("cardiac output must be positive");
  return reasons;
}

export function defaultParameterDistributions(snapshot: TwinSnapshot): readonly ParameterDistribution[] {
  const values = baselineScenarioParameters(snapshot);
  const measurement = (key: keyof CardiacTwinState["measurements"]) => snapshot.state.measurements[key];
  const make = (parameter: keyof typeof values, key: keyof CardiacTwinState["measurements"], sd: number, rationale: string): ParameterDistribution => {
    const observed = measurement(key);
    const directIndex = snapshot.state.hemodynamics[parameter as keyof typeof snapshot.state.hemodynamics];
    const directIndexSource = directIndex?.source ? String(directIndex.source) : undefined;
    const measuredDirectly = directIndexSource === "file_extraction" || directIndexSource === "user_input";
    const source = parameter === "heart_rate_bpm" && observed
      ? "measurement"
      : measuredDirectly
        ? "measurement"
        : parameter === "afterload_index" || parameter === "systemic_vascular_resistance_index"
          ? "population_prior"
          : directIndex
            ? "derived"
            : observed
              ? "derived"
              : "population_prior";
    const relevantEvidenceIds = [
      ...(observed?.evidence ? [observed.evidence] : []),
      ...(directIndex?.evidence ? [directIndex.evidence] : []),
    ].filter((evidenceId, index, all) => all.indexOf(evidenceId) === index);
    return {
      parameterId: parameter,
      family: "normal",
      parameters: { mean: values[parameter], sd },
      bounds: { min: getScenarioParameterDefinition(parameter)!.min, max: getScenarioParameterDefinition(parameter)!.max },
      source,
      evidenceIds: relevantEvidenceIds,
      ...(observed?.source || directIndexSource ? { sourceDetail: observed?.source ? String(observed.source) : directIndexSource } : {}),
      rationale,
      version: PRIOR_VERSION,
    };
  };
  return [
    make("heart_rate_bpm", "heart_rate_bpm", 3, "Heart rate is measured when present; otherwise a bounded measurement-scale prior is used."),
    make("preload_index", "edv_ml", 0.08, "Preload is a model proxy; EDV evidence narrows it when available."),
    make("afterload_index", "systolic_bp_mmhg", 0.1, "Afterload is a model proxy; blood-pressure evidence is not treated as a direct afterload measurement."),
    make("contractility_index", "ejection_fraction_pct", 0.12, "Contractility is a model proxy informed directionally by EF when available."),
    make("systemic_vascular_resistance_index", "systolic_bp_mmhg", 0.12, "SVR is not directly observed here; the prior remains explicit and bounded."),
  ];
}

export function runEnsemble(snapshot: TwinSnapshot, config: EnsembleConfig): TwinEnsemble {
  if (!Number.isSafeInteger(config.seed)) throw new RangeError("Ensemble seed must be a safe integer");
  if (!Number.isInteger(config.requestedSampleCount) || config.requestedSampleCount < 1 || config.requestedSampleCount > 1000) throw new RangeError("Sample count must be an integer between 1 and 1000");
  if (config.distributions.length === 0) throw new RangeError("At least one parameter distribution is required");
  const seen = new Set<string>();
  for (const distribution of config.distributions) {
    validateDistribution(distribution);
    if (seen.has(distribution.parameterId)) throw new RangeError(`Duplicate distribution: ${distribution.parameterId}`);
    seen.add(distribution.parameterId);
  }
  const random = createSeededRandom(config.seed);
  const resolvedVersions = {
    physiologyVersion: config.physiologyVersion ?? PHYSIOLOGY_VERSION,
    distributionConfigVersion: config.distributionConfigVersion ?? CONFIG_VERSION,
    priorVersion: config.priorVersion ?? PRIOR_VERSION,
  };
  const id = `ensemble-${hash(stableSerialize({ snapshotId: snapshot.id, timestamp: snapshot.timestamp, quality: snapshot.quality, seed: config.seed, requestedSampleCount: config.requestedSampleCount, versions: resolvedVersions, parentScenarioId: config.parentScenarioId, distributions: config.distributions }))}`;
  const samples: TwinSample[] = [];
  let rejected = 0;
  for (let index = 0; index < config.requestedSampleCount; index += 1) {
    const sampled = sampleParameters(snapshot, config.distributions, random);
    let state: CardiacTwinState = snapshot.state;
    const reasons = [...sampled.reasons];
    if (reasons.length === 0) {
      const inputs: ScenarioInput[] = Object.entries(sampled.values).map(([parameter, value]) => ({ parameter: parameter as ScenarioInput["parameter"], value }));
      try {
        state = propagateScenario(snapshot, inputs, `ensemble-${snapshot.id}-${index}`, "M5 plausible simulated twin").result.scenario.state as CardiacTwinState;
        reasons.push(...validity(state));
      } catch (error) {
        reasons.push(error instanceof Error ? error.message : "deterministic physiology rejected sample");
      }
    }
    const valid = reasons.length === 0;
    if (!valid) rejected += 1;
    samples.push(Object.freeze({ id: `${id}-sample-${index}`, index, seed: config.seed, originSnapshotId: snapshot.id, originQuality: snapshot.quality, parameters: Object.freeze({ ...sampled.values }), state, valid, rejectionReasons: Object.freeze(reasons) }));
  }
  const accepted = samples.filter((sample) => sample.valid);
  if (accepted.length === 0) throw new RangeError("No valid plausible twins were accepted");
  const distributions = METRICS.map(([metricId, unit]) => summarizeDistribution(metricId, unit, accepted.map((sample) => metricValue(sample.state, metricId)).filter((value): value is number => value != null)));
  const provenance = {
    originSnapshotId: snapshot.id,
    originTimestamp: snapshot.timestamp,
    originQuality: snapshot.quality,
    originProvenance: structuredClone(snapshot.provenance),
    evidenceIds: [...new Set([
      ...snapshot.evidenceIds,
      ...config.distributions.flatMap((distribution) => distribution.evidenceIds),
    ])],
    seed: config.seed,
    physiologyVersion: resolvedVersions.physiologyVersion,
    distributionConfigVersion: resolvedVersions.distributionConfigVersion,
    priorVersion: resolvedVersions.priorVersion,
    ...(config.parentScenarioId ? { parentScenarioId: config.parentScenarioId } : {}),
    createdAt: snapshot.timestamp,
    assumptions: ["Parameters are sampled independently because BeatIT has no validated joint correlation model for these proxies.", "Percentiles describe accepted deterministic simulations, not clinical probability or confidence intervals."],
  } as const;
  return Object.freeze({ id, originSnapshotId: snapshot.id, seed: config.seed, requestedSampleCount: config.requestedSampleCount, acceptedSampleCount: accepted.length, rejectedSampleCount: rejected, samples: Object.freeze(samples), distributions: Object.freeze(distributions), parameterDistributions: Object.freeze(config.distributions), provenance, warnings: Object.freeze(["Educational simulation only; not diagnosis or treatment advice.", ...(snapshot.quality === "synthetic" ? ["Origin snapshot is synthetic replay data; it is not patient evidence."] : []), ...(rejected ? [`${rejected} sampled twin(s) were rejected by validity checks.`] : [])]) });
}

/** Convert an M4 point scenario into a fixed-input M5 compatibility seam. */
export function distributionsForScenario(
  distributions: readonly ParameterDistribution[],
  scenario: ScenarioDefinition,
): readonly ParameterDistribution[] {
  const changes = new Map(scenario.parameters.map((change) => [change.parameter, change.value]));
  return distributions.map((distribution) => {
    const value = changes.get(distribution.parameterId);
    if (value === undefined) return distribution;
    return {
      ...distribution,
      family: "fixed",
      parameters: { value },
      source: "scenario",
      rationale: `Fixed by M4 ScenarioDefinition ${scenario.id}; ensemble execution remains deterministic per sampled origin.`,
    };
  });
}

export function chooseRepresentatives(ensemble: TwinEnsemble, metricId: EnsembleMetricId = "ejection_fraction_pct"): EnsembleRepresentatives {
  const valid = ensemble.samples.filter((sample) => sample.valid);
  if (valid.length === 0) return { median: null, low: null, high: null };
  const value = (sample: TwinSample) => metricValue(sample.state, metricId) ?? Number.NaN;
  const sorted = [...valid].sort((a, b) => value(a) - value(b));
  const target = ensemble.distributions.find((distribution) => distribution.metricId === metricId)?.median ?? value(sorted[Math.floor((sorted.length - 1) / 2)]!);
  const median = [...sorted].sort((a, b) => Math.abs(value(a) - target) - Math.abs(value(b) - target))[0] ?? null;
  return { low: sorted[0] ?? null, high: sorted[sorted.length - 1] ?? null, median };
}

export function ensembleCacheKey(snapshot: TwinSnapshot, config: EnsembleConfig): string {
  return hash(stableSerialize({ snapshotId: snapshot.id, timestamp: snapshot.timestamp, config }));
}
