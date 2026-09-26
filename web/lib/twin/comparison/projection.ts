import type { CardiacTwinState, SimulationVisualization } from "@/types/heart";
import type { ShadowTrialPair, ShadowTrialScenarioDefinition } from "@/types/shadow-trial";
import type { PairedHeartState } from "@/lib/twin/comparison/contracts";

function measured(state: CardiacTwinState, key: keyof CardiacTwinState["measurements"]): number | null {
  const entry = state.measurements[key];
  return typeof entry?.value === "number" && Number.isFinite(entry.value) ? entry.value : null;
}

function hemodynamic(state: CardiacTwinState, key: keyof CardiacTwinState["hemodynamics"]): number | null {
  const entry = state.hemodynamics[key];
  return typeof entry?.value === "number" && Number.isFinite(entry.value) ? entry.value : null;
}

/** Project canonical M6 scalar state into existing visual channels without recomputing physiology. */
export function projectPairedState(state: CardiacTwinState, reference: SimulationVisualization, label: string): SimulationVisualization {
  const hr = measured(state, "heart_rate_bpm") ?? reference.summary.heart_rate_bpm;
  const ef = measured(state, "ejection_fraction_pct") ?? reference.summary.ef_pct;
  const sv = measured(state, "stroke_volume_ml") ?? reference.summary.stroke_volume_ml;
  const co = measured(state, "cardiac_output_l_min") ?? reference.summary.cardiac_output_l_min;
  const rr = measured(state, "heart_rate_bpm") ? 60000 / Math.max(1, hr) : reference.electrophysiology.rr_interval_ms ?? 60000 / Math.max(1, hr);
  const referenceHeart = reference["3d_heart"];
  return {
    ...reference,
    cardiac_findings: undefined,
    summary: {
      ...reference.summary,
      heart_rate_bpm: hr,
      ef_pct: ef,
      ejection_fraction_pct: ef,
      stroke_volume_ml: sv,
      cardiac_output_l_min: co,
      preload_index: hemodynamic(state, "preload_index") ?? reference.summary.preload_index,
      afterload_index: hemodynamic(state, "afterload_index") ?? reference.summary.afterload_index,
      contractility_index: hemodynamic(state, "contractility_index") ?? reference.summary.contractility_index,
      svr_index: hemodynamic(state, "systemic_vascular_resistance_index") ?? reference.summary.svr_index,
      simulation_label: label,
    },
    cardiac_cycle: { ...reference.cardiac_cycle, heart_rate_bpm: hr, cycle_duration_ms: 60000 / Math.max(1, hr), stroke_volume_ml: sv, cardiac_output_l_min: co },
    pv_loop: { ...reference.pv_loop, ef_pct: ef, simulation_label: `${label} · PV shape held from source visualization` },
    electrophysiology: { ...reference.electrophysiology, rr_interval_ms: rr },
    ...(referenceHeart ? { "3d_heart": { ...referenceHeart, heart_rate_bpm: hr, beat_interval_ms: rr, contractility_index: hemodynamic(state, "contractility_index") ?? referenceHeart.contractility_index, afterload_index: hemodynamic(state, "afterload_index") ?? referenceHeart.afterload_index, preload_index: hemodynamic(state, "preload_index") ?? referenceHeart.preload_index, simulation_label: label } } : {}),
    simulation_note: `${reference.simulation_note} · ${label}; hypothetical educational projection`,
  };
}

export function pairedHeartStateFromM6(trialId: string, pair: ShadowTrialPair, reference: SimulationVisualization, scenarioDefinition: ShadowTrialScenarioDefinition | null = null): PairedHeartState | null {
  if (!pair.valid || pair.baseline_twin_id !== pair.sample_id || pair.scenario_twin_id === pair.sample_id) return null;
  return { pairId: pair.sample_id, trialId, baselineSampleId: pair.sample_id, scenarioSampleId: pair.scenario_twin_id, baselineState: pair.baseline_state, scenarioState: pair.scenario_state, baselineVisualization: projectPairedState(pair.baseline_state, reference, "M7 baseline paired state"), scenarioVisualization: projectPairedState(pair.scenario_state, reference, "M7 counterfactual paired state"), scenarioDefinition, pair };
}
