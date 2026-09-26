import type { Simulation3DHeart } from "@/types/heart";
import type { ScenarioResult } from "@/lib/twin/scenario/types";

/**
 * Map scenario values into existing visualization controls. This changes
 * timing/intensity inputs only; it does not claim geometric measurements.
 */
export function scenarioHeartBinding(
  result: ScenarioResult,
  baseline: Simulation3DHeart | null | undefined,
): Simulation3DHeart | null {
  if (!baseline) return null;
  const state = result.scenario.state;
  const value = (entry: { value: number } | null | undefined, fallback: number) => entry?.value ?? fallback;
  const hr = value(state.measurements.heart_rate_bpm, baseline.heart_rate_bpm);
  const contractility = value(state.hemodynamics.contractility_index, baseline.contractility_index);
  return {
    ...baseline,
    heart_rate_bpm: hr,
    beat_interval_ms: 60000 / Math.max(1, hr),
    contractility_index: contractility,
    afterload_index: value(state.hemodynamics.afterload_index, baseline.afterload_index),
    preload_index: value(state.hemodynamics.preload_index, baseline.preload_index),
    beat_amplitude: Math.max(0.1, baseline.beat_amplitude * (0.8 + contractility * 0.2)),
    simulation_label: "M4 hypothetical scenario · visual binding",
  };
}
