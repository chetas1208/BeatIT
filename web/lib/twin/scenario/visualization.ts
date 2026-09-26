import type { SimulationVisualization } from "@/types/heart";
import type { ScenarioResult } from "@/lib/twin/scenario/types";
import { scenarioHeartBinding } from "@/lib/twin/scenario/heart";
import { scenarioPvLoop } from "@/lib/twin/scenario/pv";

function value(entry: { value: number } | null | undefined): number | null {
  return typeof entry?.value === "number" && Number.isFinite(entry.value) ? entry.value : null;
}

/** Project a deterministic scenario into the existing visual channels. */
export function scenarioVisualization(
  result: ScenarioResult,
  baseline: SimulationVisualization | null | undefined,
): SimulationVisualization | null {
  if (!baseline) return null;
  const measurements = result.scenario.state.measurements;
  const hemodynamics = result.scenario.state.hemodynamics;
  const hr = value(measurements.heart_rate_bpm) ?? baseline.summary.heart_rate_bpm;
  const ef = value(measurements.ejection_fraction_pct) ?? baseline.summary.ef_pct;
  const sv = value(measurements.stroke_volume_ml) ?? baseline.summary.stroke_volume_ml;
  const co = value(measurements.cardiac_output_l_min) ?? baseline.summary.cardiac_output_l_min;
  const projectedPv = scenarioPvLoop(result, baseline);
  const projectedHeart = scenarioHeartBinding(result, baseline["3d_heart"]);
  return {
    ...baseline,
    summary: {
      ...baseline.summary,
      heart_rate_bpm: hr,
      ef_pct: ef,
      ejection_fraction_pct: ef,
      stroke_volume_ml: sv,
      cardiac_output_l_min: co,
      preload_index: value(hemodynamics.preload_index) ?? baseline.summary.preload_index,
      afterload_index: value(hemodynamics.afterload_index) ?? baseline.summary.afterload_index,
      contractility_index: value(hemodynamics.contractility_index) ?? baseline.summary.contractility_index,
      svr_index: value(hemodynamics.systemic_vascular_resistance_index) ?? baseline.summary.svr_index,
      simulation_label: "M4 hypothetical scenario",
    },
    pv_loop: projectedPv ?? { ...baseline.pv_loop, simulation_label: "M4 hypothetical scenario · PV unavailable" },
    cardiac_cycle: {
      ...baseline.cardiac_cycle,
      heart_rate_bpm: hr,
      cycle_duration_ms: 60000 / Math.max(1, hr),
      stroke_volume_ml: sv,
      cardiac_output_l_min: co,
    },
    electrophysiology: {
      ...baseline.electrophysiology,
      rr_interval_ms: 60000 / Math.max(1, hr),
    },
    ...(projectedHeart ? { "3d_heart": projectedHeart } : {}),
    simulation_note: `${baseline.simulation_note} · hypothetical deterministic scenario`,
  };
}
