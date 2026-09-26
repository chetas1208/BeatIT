import type { CardiacTwinState, SimulationVisualization } from "@/types/heart";

function value(
  state: CardiacTwinState,
  key: keyof CardiacTwinState["measurements"],
): number | null {
  const entry = state.measurements[key];
  return typeof entry?.value === "number" && Number.isFinite(entry.value)
    ? entry.value
    : null;
}

/**
 * Bind an already-computed paired state to the existing visual template.
 * This is deliberately a projection: it does not calculate physiology or
 * mutate either state returned by the Shadow Trial.
 */
export function comparisonVisualization(
  state: CardiacTwinState,
  template: SimulationVisualization,
  label: string,
): SimulationVisualization {
  const heartRate = value(state, "heart_rate_bpm") ?? template.summary.heart_rate_bpm;
  const ef = value(state, "ejection_fraction_pct") ?? template.summary.ef_pct;
  const sv = value(state, "stroke_volume_ml") ?? template.summary.stroke_volume_ml;
  const co = value(state, "cardiac_output_l_min") ?? template.summary.cardiac_output_l_min;
  const rr = 60000 / Math.max(1, heartRate);

  return {
    ...template,
    cardiac_findings: undefined,
    summary: {
      ...template.summary,
      heart_rate_bpm: heartRate,
      ef_pct: ef,
      ejection_fraction_pct: ef,
      stroke_volume_ml: sv,
      cardiac_output_l_min: co,
      simulation_label: label,
    },
    cardiac_cycle: {
      ...template.cardiac_cycle,
      heart_rate_bpm: heartRate,
      cycle_duration_ms: rr,
      stroke_volume_ml: sv,
      cardiac_output_l_min: co,
    },
    pv_loop: {
      ...template.pv_loop,
      ef_pct: ef,
      simulation_label: `${label} · baseline PV shape held`,
    },
    electrophysiology: {
      ...template.electrophysiology,
      rr_interval_ms: rr,
    },
    simulation_note: `${template.simulation_note} · ${label}; educational projection only`,
  };
}
