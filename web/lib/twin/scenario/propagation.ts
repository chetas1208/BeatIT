import type { CardiacTwinState, MeasuredValue } from "@/types/heart";
import type {
  CausalEdge,
  CausalGraph,
  CausalNode,
  CausalPath,
  CausalPropagationResult,
  CausalSource,
  CausalValueDelta,
} from "@/lib/twin/scenario/causal";
import type {
  ComponentDelta,
  ObservedOriginMetadata,
  ScenarioParameterChange,
  ScenarioResult,
  ScenarioTwinState,
} from "@/lib/twin/scenario/types";
import { getScenarioParameterDefinition, validateScenarioParameter } from "@/lib/twin/scenario/parameters";
import type { TwinSnapshot } from "@/lib/twin/time/contracts";
import { normalizeTwinTimestamp } from "@/lib/twin/time/contracts";

export type ScenarioParameterKey =
  | "heart_rate_bpm"
  | "preload_index"
  | "afterload_index"
  | "contractility_index"
  | "systemic_vascular_resistance_index";

export interface ScenarioInput {
  readonly parameter: ScenarioParameterKey;
  readonly value: number;
}

interface BaselineMetrics {
  hr: number;
  edv: number;
  esv: number;
  map: number;
  co: number;
  sv: number;
  ef: number;
  preload: number;
  afterload: number;
  contractility: number;
  svr: number;
}

interface ScenarioMetrics extends BaselineMetrics {
  readonly rr: number;
}

const SOURCE: CausalSource = {
  id: "beatit-deterministic-m4",
  kind: "deterministic_formula",
  label: "BeatIT bounded educational physiology",
  reference: "python/hearttwin/tools/cardiac_state.py",
  method: "explicit-input scenario propagation",
  note: "Scenario values are hypothetical and are not clinical predictions.",
};

const GRAPH_NODES = [
  ["heart_rate", "Heart rate", "parameter", "heart_rate", "bpm"],
  ["preload", "Preload", "parameter", "preload", "index"],
  ["afterload", "Afterload", "parameter", "afterload", "index"],
  ["contractility", "Contractility", "parameter", "contractility", "index"],
  ["svr", "Systemic vascular resistance", "parameter", "svr", "index"],
  ["edv", "End-diastolic volume", "intermediate", "edv", "mL"],
  ["esv", "End-systolic volume", "intermediate", "esv", "mL"],
  ["stroke_volume", "Stroke volume", "observable", "sv", "mL"],
  ["cardiac_output", "Cardiac output", "outcome", "co", "L/min"],
  ["map", "Mean arterial pressure", "observable", "map", "mmHg"],
];

const EDGES: readonly CausalEdge[] = [
  { id: "preload-edv", from: "preload", to: "edv", relation: "increases", sign: 1, sourceIds: [SOURCE.id] },
  { id: "afterload-esv", from: "afterload", to: "esv", relation: "increases", sign: 1, sourceIds: [SOURCE.id] },
  { id: "contractility-esv", from: "contractility", to: "esv", relation: "decreases", sign: -1, sourceIds: [SOURCE.id] },
  { id: "edv-sv", from: "edv", to: "stroke_volume", relation: "derives", sign: 1, sourceIds: [SOURCE.id] },
  { id: "esv-sv", from: "esv", to: "stroke_volume", relation: "derives", sign: -1, sourceIds: [SOURCE.id] },
  { id: "hr-co", from: "heart_rate", to: "cardiac_output", relation: "increases", sign: 1, sourceIds: [SOURCE.id] },
  { id: "sv-co", from: "stroke_volume", to: "cardiac_output", relation: "increases", sign: 1, sourceIds: [SOURCE.id] },
  { id: "svr-map", from: "svr", to: "map", relation: "increases", sign: 1, sourceIds: [SOURCE.id] },
];

export const M4_CAUSAL_GRAPH: CausalGraph = {
  id: "beatit-m4-hemodynamics",
  version: "1.0.0",
  nodes: GRAPH_NODES.map(([id, label, kind, variable, unit]) => ({ id, label, kind: kind as CausalNode["kind"], variable, unit, sourceIds: [SOURCE.id] })),
  edges: EDGES,
  sources: [SOURCE],
};

function readMeasured(value: MeasuredValue | null | undefined, fallback: number): number {
  return typeof value?.value === "number" && Number.isFinite(value.value) ? value.value : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function deepFreeze<T>(value: T, seen = new WeakSet<object>()): T {
  if (value === null || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  for (const child of Object.values(value)) deepFreeze(child, seen);
  return Object.freeze(value);
}

function baselineMetrics(state: CardiacTwinState): BaselineMetrics {
  const hr = clamp(readMeasured(state.measurements.heart_rate_bpm, 70), 30, 220);
  const edv = clamp(readMeasured(state.measurements.edv_ml, 130), 40, 400);
  const ef = clamp(readMeasured(state.measurements.ejection_fraction_pct, 60), 5, 90);
  const defaultEsv = edv * (1 - ef / 100);
  const esv = clamp(readMeasured(state.measurements.esv_ml, defaultEsv), 5, edv - 1);
  const sv = Math.max(1, edv - esv);
  const co = Math.max(0.1, hr * sv / 1000);
  const sbp = readMeasured(state.measurements.systolic_bp_mmhg, 120);
  const dbp = readMeasured(state.measurements.diastolic_bp_mmhg, 80);
  const map = dbp + Math.max(0, sbp - dbp) / 3;
  return {
    hr, edv, esv, map, co, sv,
    ef: (sv / edv) * 100,
    preload: readMeasured(state.hemodynamics.preload_index, 1),
    afterload: readMeasured(state.hemodynamics.afterload_index, 1),
    contractility: readMeasured(state.hemodynamics.contractility_index, 1),
    svr: readMeasured(state.hemodynamics.systemic_vascular_resistance_index, 1),
  };
}

function parameterValue(inputs: readonly ScenarioInput[], key: ScenarioParameterKey, fallback: number): number {
  return inputs.find((input) => input.parameter === key)?.value ?? fallback;
}

function evaluate(base: BaselineMetrics, inputs: readonly ScenarioInput[]): ScenarioMetrics {
  const bounded = (key: ScenarioParameterKey, fallback: number) => {
    const definition = getScenarioParameterDefinition(key);
    const value = parameterValue(inputs, key, fallback);
    return definition ? clamp(value, definition.min, definition.max) : value;
  };
  const hr = bounded("heart_rate_bpm", base.hr);
  const preload = bounded("preload_index", base.preload);
  const afterload = bounded("afterload_index", base.afterload);
  const contractility = bounded("contractility_index", base.contractility);
  const svr = bounded("systemic_vascular_resistance_index", base.svr);
  const preloadFactor = base.preload > 0 ? preload / base.preload : 1;
  const afterloadFactor = base.afterload > 0 ? afterload / base.afterload : 1;
  const contractilityFactor = base.contractility > 0 ? contractility / base.contractility : 1;
  const svrFactor = base.svr > 0 ? svr / base.svr : 1;
  const edv = clamp(base.edv * preloadFactor, 40, 400);
  // Bounded educational relationship: increased afterload raises ESV, while
  // increased contractility lowers it. This is intentionally not a clinical
  // patient-specific model and is documented as such in M4 docs.
  const esv = clamp(base.esv + base.sv * 0.55 * (afterloadFactor - 1) - base.esv * 0.5 * (contractilityFactor - 1), 5, edv - 1);
  const sv = Math.max(1, edv - esv);
  const co = Math.max(0.1, hr * sv / 1000);
  const map = Math.max(20, base.map * (1 + 0.35 * (svrFactor - 1) + 0.1 * ((co / base.co) - 1)));
  return {
    hr, edv, esv, map, co, sv,
    ef: (sv / edv) * 100,
    preload, afterload, contractility, svr,
    rr: 60000 / hr,
  };
}

function measured(value: number, unit: string, method: string): MeasuredValue {
  return { value: Number(value.toFixed(4)), unit, source: "derived", confidence: 1, method, evidence: "M4 deterministic scenario derivation" };
}

function updateState(source: CardiacTwinState, metrics: ScenarioMetrics): CardiacTwinState {
  const state: CardiacTwinState = structuredClone(source);
  state.measurements = {
    ...state.measurements,
    heart_rate_bpm: measured(metrics.hr, "bpm", "scenario heart-rate input"),
    edv_ml: measured(metrics.edv, "mL", "preload → EDV"),
    esv_ml: measured(metrics.esv, "mL", "afterload/contractility → ESV"),
    stroke_volume_ml: measured(metrics.sv, "mL", "SV = EDV - ESV"),
    ejection_fraction_pct: measured(metrics.ef, "%", "EF = SV / EDV × 100"),
    cardiac_output_l_min: measured(metrics.co, "L/min", "CO = HR × SV / 1000"),
  };
  state.hemodynamics = {
    ...state.hemodynamics,
    preload_index: measured(metrics.preload, "index", "scenario preload input"),
    afterload_index: measured(metrics.afterload, "index", "scenario afterload input"),
    contractility_index: measured(metrics.contractility, "index", "scenario contractility input"),
    systemic_vascular_resistance_index: measured(metrics.svr, "index", "scenario SVR input"),
  };
  state.electrophysiology = {
    ...state.electrophysiology,
    rr_interval_ms: measured(metrics.rr, "ms", "RR = 60000 / HR"),
  };
  state.warnings = [...state.warnings, "Hypothetical M4 scenario; not clinical evidence or treatment advice."];
  return state;
}

function originFor(snapshot: TwinSnapshot): ObservedOriginMetadata {
  return {
    snapshotId: snapshot.id,
    patientId: snapshot.state.case_id,
    timestamp: snapshot.timestamp,
    state: structuredClone(snapshot.state),
    provenance: structuredClone(snapshot.provenance),
    evidenceIds: snapshot.evidenceIds.slice(),
    quality: snapshot.quality,
  };
}

function deltaNode(nodeId: string, variable: string, unit: string, baseline: number, scenario: number): CausalValueDelta {
  return { nodeId, variable, unit, baseline, scenario, delta: scenario - baseline, sourceIds: [SOURCE.id] };
}

function path(id: string, nodeIds: readonly string[], sign: -1 | 0 | 1): CausalPath {
  const edgeIds = EDGES.filter((edge) => nodeIds.includes(edge.from) && nodeIds.includes(edge.to)).map((edge) => edge.id);
  return { id, from: nodeIds[0]!, to: nodeIds[nodeIds.length - 1]!, nodeIds, edgeIds, sign, sourceIds: [SOURCE.id] };
}

export function createScenarioInputs(base: BaselineMetrics): ScenarioInput[] {
  return [
    { parameter: "heart_rate_bpm", value: base.hr },
    { parameter: "preload_index", value: base.preload },
    { parameter: "afterload_index", value: base.afterload },
    { parameter: "contractility_index", value: base.contractility },
    { parameter: "systemic_vascular_resistance_index", value: base.svr },
  ];
}

export function baselineScenarioParameters(snapshot: TwinSnapshot): Record<ScenarioParameterKey, number> {
  const base = baselineMetrics(snapshot.state);
  return {
    heart_rate_bpm: base.hr,
    preload_index: base.preload,
    afterload_index: base.afterload,
    contractility_index: base.contractility,
    systemic_vascular_resistance_index: base.svr,
  };
}

export function propagateScenario(
  snapshot: TwinSnapshot,
  inputs: readonly ScenarioInput[],
  scenarioId = `scenario-${snapshot.id}`,
  label = "M4 hypothetical scenario",
): { result: ScenarioResult; propagation: CausalPropagationResult } {
  const seenParameters = new Set<string>();
  for (const input of inputs) {
    if (seenParameters.has(input.parameter)) {
      throw new RangeError(`Duplicate scenario parameter: ${input.parameter}`);
    }
    seenParameters.add(input.parameter);
    const error = validateScenarioParameter(input.parameter, input.value);
    if (error) throw new RangeError(error);
  }
  const base = baselineMetrics(snapshot.state);
  const metrics = evaluate(base, inputs);
  const scenarioState = updateState(snapshot.state, metrics);
  // The selected snapshot timestamp is the stable scenario origin. The
  // computation has no wall-clock dependency, so identical inputs serialize
  // identically and can be replayed deterministically.
  const createdAt = normalizeTwinTimestamp(snapshot.timestamp);
  const changes: ScenarioParameterChange[] = inputs.map((input) => ({
    parameter: input.parameter,
    baseline: input.parameter === "heart_rate_bpm" ? base.hr
      : input.parameter === "preload_index" ? base.preload
        : input.parameter === "afterload_index" ? base.afterload
          : input.parameter === "contractility_index" ? base.contractility : base.svr,
    value: input.value,
    delta: input.value - (input.parameter === "heart_rate_bpm" ? base.hr
      : input.parameter === "preload_index" ? base.preload
        : input.parameter === "afterload_index" ? base.afterload
          : input.parameter === "contractility_index" ? base.contractility : base.svr),
    unit: input.parameter === "heart_rate_bpm" ? "bpm" : "index",
  }));
  const origin = deepFreeze(originFor(snapshot));
  const definition = { id: scenarioId, label, description: "Deterministic bounded counterfactual; observed history is unchanged.", origin, parameters: changes, createdAt } as const;
  const scenario: ScenarioTwinState = deepFreeze({
    scenarioId,
    origin,
    state: scenarioState,
    timestamp: createdAt,
    provenance: [{ source: "derived_model", method: "M4 deterministic scenario engine", evidenceIds: snapshot.evidenceIds.slice(), note: "Hypothetical only." }],
  });
  const deltas: CausalValueDelta[] = [
    deltaNode("heart_rate", "heart_rate", "bpm", base.hr, metrics.hr),
    deltaNode("preload", "preload", "index", base.preload, metrics.preload),
    deltaNode("afterload", "afterload", "index", base.afterload, metrics.afterload),
    deltaNode("contractility", "contractility", "index", base.contractility, metrics.contractility),
    deltaNode("svr", "svr", "index", base.svr, metrics.svr),
    deltaNode("edv", "edv", "mL", base.edv, metrics.edv),
    deltaNode("esv", "esv", "mL", base.esv, metrics.esv),
    deltaNode("stroke_volume", "sv", "mL", base.sv, metrics.sv),
    deltaNode("cardiac_output", "co", "L/min", base.co, metrics.co),
    deltaNode("map", "map", "mmHg", base.map, metrics.map),
  ];
  const inputNodeIds = inputs.map((input) => input.parameter === "heart_rate_bpm" ? "heart_rate" : input.parameter === "preload_index" ? "preload" : input.parameter === "afterload_index" ? "afterload" : input.parameter === "contractility_index" ? "contractility" : "svr");
  const affectedNodeIds = deltas.filter((delta) => Math.abs(delta.delta ?? 0) > 1e-9).map((delta) => delta.nodeId);
  const paths = [
    path("afterload-to-output", ["afterload", "esv", "stroke_volume", "cardiac_output"], -1),
    path("preload-to-output", ["preload", "edv", "stroke_volume", "cardiac_output"], 1),
    path("contractility-to-output", ["contractility", "esv", "stroke_volume", "cardiac_output"], 1),
    path("svr-to-map", ["svr", "map"], 1),
  ];
  const propagation: CausalPropagationResult = {
    graphId: M4_CAUSAL_GRAPH.id,
    graphVersion: M4_CAUSAL_GRAPH.version,
    status: "complete",
    inputNodeIds,
    affectedNodeIds,
    deltas,
    paths,
    sources: [SOURCE],
    warnings: ["Bounded educational relationships; not calibrated for clinical prediction."],
    deterministic: true,
  };
  const componentDeltas: ComponentDelta[] = [
    { componentId: "left-ventricle", metric: "stroke_volume_ml", baseline: base.sv, scenario: metrics.sv, delta: metrics.sv - base.sv, unit: "mL", direction: metrics.sv === base.sv ? "unchanged" : metrics.sv > base.sv ? "increase" : "decrease", provenance: scenario.provenance },
    { componentId: "left-ventricle", metric: "ejection_fraction_pct", baseline: base.ef, scenario: metrics.ef, delta: metrics.ef - base.ef, unit: "%", direction: metrics.ef === base.ef ? "unchanged" : metrics.ef > base.ef ? "increase" : "decrease", provenance: scenario.provenance },
    { componentId: "blood-flow", metric: "cardiac_output_l_min", baseline: base.co, scenario: metrics.co, delta: metrics.co - base.co, unit: "L/min", direction: metrics.co === base.co ? "unchanged" : metrics.co > base.co ? "increase" : "decrease", provenance: scenario.provenance },
  ];
  const result: ScenarioResult = deepFreeze({ definition, baseline: origin, scenario, componentDeltas, provenance: scenario.provenance, status: "computed", warnings: propagation.warnings, computedAt: createdAt, causal: propagation });
  return {
    result,
    propagation,
  };
}

export function scenarioMetrics(snapshot: TwinSnapshot, inputs: readonly ScenarioInput[]): ScenarioMetrics {
  return evaluate(baselineMetrics(snapshot.state), inputs);
}
