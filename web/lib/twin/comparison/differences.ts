import type { ShadowTrialMetricId, ShadowTrialPair } from "@/types/shadow-trial";

export type DifferenceDirection = "positive" | "neutral" | "negative";
export type DifferenceKind = "absolute" | "percentage_points";
export type PairInput = Pick<ShadowTrialPair, "valid" | "deltas"> & Partial<ShadowTrialPair>;

export interface DifferencePolicy { readonly label: string; readonly unit: string; readonly neutralTolerance: number; readonly kind: DifferenceKind; readonly decimalPlaces: number; }
export interface DisplayMetricDelta { readonly metricId: ShadowTrialMetricId; readonly baseline: number | null; readonly counterfactual: number | null; readonly absoluteDelta: number; readonly relativeDelta: number | null; readonly unit: string; readonly absoluteSemantics: "counterfactual_minus_baseline"; readonly relativeSemantics: "percent_change_from_baseline" | null; }
export interface ComparisonMetricDelta { readonly id: ShadowTrialMetricId; readonly label: string; readonly baseline: number | null; readonly scenario: number | null; readonly delta: number; readonly valueUnit: string; readonly deltaUnit: string; readonly direction: "increase" | "decrease"; readonly changed: true; }
export interface DisplayDifference { readonly metricId: ShadowTrialMetricId; readonly label: string; readonly delta: number; readonly unit: string; readonly neutralTolerance: number; readonly direction: Exclude<DifferenceDirection, "neutral">; readonly kind: DifferenceKind; readonly displayValue: string; }

export const SHADOW_TRIAL_METRIC_ORDER: readonly ShadowTrialMetricId[] = ["ejection_fraction_pct", "stroke_volume_ml", "cardiac_output_l_min", "heart_rate_bpm", "map_mmhg", "edv_ml", "esv_ml", "pv_loop_area_index"];
export const SHADOW_TRIAL_DIFFERENCE_POLICIES: Readonly<Record<ShadowTrialMetricId, DifferencePolicy>> = {
  ejection_fraction_pct: { label: "Ejection fraction", unit: "percentage points", neutralTolerance: 0.01, kind: "percentage_points", decimalPlaces: 2 },
  stroke_volume_ml: { label: "Stroke volume", unit: "mL", neutralTolerance: 0.01, kind: "absolute", decimalPlaces: 2 },
  cardiac_output_l_min: { label: "Cardiac output", unit: "L/min", neutralTolerance: 0.001, kind: "absolute", decimalPlaces: 3 },
  heart_rate_bpm: { label: "Heart rate", unit: "bpm", neutralTolerance: 0.01, kind: "absolute", decimalPlaces: 2 },
  map_mmhg: { label: "Mean arterial pressure", unit: "mmHg", neutralTolerance: 0.01, kind: "absolute", decimalPlaces: 2 },
  edv_ml: { label: "End-diastolic volume", unit: "mL", neutralTolerance: 0.01, kind: "absolute", decimalPlaces: 2 },
  esv_ml: { label: "End-systolic volume", unit: "mL", neutralTolerance: 0.01, kind: "absolute", decimalPlaces: 2 },
  pv_loop_area_index: { label: "PV loop area", unit: "index", neutralTolerance: 0.001, kind: "absolute", decimalPlaces: 3 },
};

function stateMetric(state: ShadowTrialPair["baseline_state"] | undefined, metricId: ShadowTrialMetricId): number | null {
  if (!state) return null;
  if (metricId === "pv_loop_area_index") {
    const value = state.hemodynamics?.pv_loop_area_index?.value;
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  }
  const entry = state.measurements?.[metricId as keyof typeof state.measurements];
  return typeof entry?.value === "number" && Number.isFinite(entry.value) ? entry.value : null;
}

function isMetricId(value: string): value is ShadowTrialMetricId { return Object.prototype.hasOwnProperty.call(SHADOW_TRIAL_DIFFERENCE_POLICIES, value); }
export function getDifferencePolicy(metricId: ShadowTrialMetricId): DifferencePolicy { return SHADOW_TRIAL_DIFFERENCE_POLICIES[metricId]; }

function formatDelta(delta: number, policy: DifferencePolicy): string { const value = Object.is(delta, -0) ? 0 : delta; return `${value > 0 ? "+" : ""}${value.toFixed(policy.decimalPlaces)} ${policy.unit}`; }

export function buildMetricDelta(pair: PairInput, metricId: ShadowTrialMetricId): DisplayMetricDelta | null {
  if (!pair.valid) return null;
  const delta = pair.deltas[metricId];
  if (typeof delta !== "number" || !Number.isFinite(delta)) return null;
  const policy = getDifferencePolicy(metricId);
  const suppliedUnit = pair.delta_units?.[metricId];
  if (suppliedUnit && suppliedUnit !== policy.unit) throw new RangeError(`Delta unit for ${metricId} does not match ${policy.unit}`);
  if (Math.abs(delta) <= policy.neutralTolerance) return null;
  const baseline = stateMetric(pair.baseline_state, metricId);
  const scenario = stateMetric(pair.scenario_state, metricId);
  const relative = baseline !== null && baseline !== 0 ? (delta / baseline) * 100 : null;
  return { metricId, baseline, counterfactual: scenario, absoluteDelta: delta, relativeDelta: relative, unit: policy.unit, absoluteSemantics: "counterfactual_minus_baseline", relativeSemantics: relative === null ? null : "percent_change_from_baseline" };
}

export function buildMetricDeltas(pair: PairInput, metricIds: readonly ShadowTrialMetricId[] = SHADOW_TRIAL_METRIC_ORDER): readonly DisplayMetricDelta[] {
  const requested = new Set(metricIds);
  return SHADOW_TRIAL_METRIC_ORDER.flatMap((metricId) => requested.has(metricId) ? (buildMetricDelta(pair, metricId) ? [buildMetricDelta(pair, metricId)!] : []) : []);
}
export const buildShadowTrialMetricDeltas = buildMetricDeltas;

export function buildDisplayDifference(pair: PairInput, metricId: ShadowTrialMetricId): DisplayDifference | null {
  const difference = buildMetricDelta(pair, metricId);
  if (!difference) return null;
  const policy = getDifferencePolicy(metricId);
  return { metricId, label: policy.label, delta: difference.absoluteDelta, unit: policy.unit, neutralTolerance: policy.neutralTolerance, direction: difference.absoluteDelta > 0 ? "positive" : "negative", kind: policy.kind, displayValue: formatDelta(difference.absoluteDelta, policy) };
}
export function buildDisplayDifferences(pair: PairInput, metricIds: readonly ShadowTrialMetricId[] = SHADOW_TRIAL_METRIC_ORDER): readonly DisplayDifference[] { return [...new Set(metricIds)].filter(isMetricId).flatMap((metricId) => { const difference = buildDisplayDifference(pair, metricId); return difference ? [difference] : []; }); }

export function buildComparisonDeltas(pair: ShadowTrialPair): ComparisonMetricDelta[] {
  return buildMetricDeltas(pair).map((difference) => ({ id: difference.metricId, label: getDifferencePolicy(difference.metricId).label, baseline: difference.baseline, scenario: difference.counterfactual, delta: difference.absoluteDelta, valueUnit: difference.metricId === "ejection_fraction_pct" ? "%" : difference.unit, deltaUnit: difference.unit, direction: difference.absoluteDelta > 0 ? "increase" : "decrease", changed: true }));
}
