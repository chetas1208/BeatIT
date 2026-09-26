import type { SimulationVisualization } from "@/types/heart";
import type { TwinSample } from "@/lib/twin/ensemble/contracts";

function value(state: TwinSample["state"], key: keyof TwinSample["state"]["measurements"]): number | null {
  const entry = state.measurements[key];
  return typeof entry?.value === "number" && Number.isFinite(entry.value) ? entry.value : null;
}

/** Project a selected plausible twin into existing visual channels. */
export function plausibleTwinVisualization(sample: TwinSample, baseline: SimulationVisualization | null | undefined): SimulationVisualization | null {
  if (!baseline) return null;
  const hr = value(sample.state, "heart_rate_bpm") ?? baseline.summary.heart_rate_bpm;
  const ef = value(sample.state, "ejection_fraction_pct") ?? baseline.summary.ef_pct;
  const sv = value(sample.state, "stroke_volume_ml") ?? baseline.summary.stroke_volume_ml;
  const co = value(sample.state, "cardiac_output_l_min") ?? baseline.summary.cardiac_output_l_min;
  const rr = 60000 / Math.max(1, hr);
  return {
    ...baseline,
    cardiac_findings: undefined,
    summary: { ...baseline.summary, heart_rate_bpm: hr, ef_pct: ef, ejection_fraction_pct: ef, stroke_volume_ml: sv, cardiac_output_l_min: co, simulation_label: "M5 plausible scalar projection" },
    cardiac_cycle: { ...baseline.cardiac_cycle, heart_rate_bpm: hr, cycle_duration_ms: rr, stroke_volume_ml: sv, cardiac_output_l_min: co },
    pv_loop: { ...baseline.pv_loop, ef_pct: ef, simulation_label: "M5 scalar projection · baseline PV shape held" },
    electrophysiology: { ...baseline.electrophysiology, rr_interval_ms: rr },
    simulation_note: `${baseline.simulation_note} · selected plausible scalar twin; baseline PV shape held; educational only`,
  };
}
