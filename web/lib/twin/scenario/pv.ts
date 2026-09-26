import type { PVLoopData, SimulationVisualization } from "@/types/heart";
import type { ScenarioResult } from "@/lib/twin/scenario/types";

function scaleLoop(loop: PVLoopData, baselineEdv: number, baselineEsv: number, scenarioEdv: number, scenarioEsv: number): PVLoopData {
  const volumeSpan = Math.max(1, baselineEdv - baselineEsv);
  const scenarioSpan = Math.max(1, scenarioEdv - scenarioEsv);
  const volume = loop.volume_ml.map((value) => scenarioEsv + ((value - baselineEsv) / volumeSpan) * scenarioSpan);
  const pressureScale = scenarioSpan / volumeSpan;
  const pressure = loop.pressure_mmhg.map((value) => Math.max(0, value * (0.92 + pressureScale * 0.08)));
  return {
    ...loop,
    volume_ml: volume,
    pressure_mmhg: pressure,
    pv_loop_area_mmhg_ml: Math.max(0, loop.pv_loop_area_mmhg_ml * pressureScale),
    stroke_work_j: Math.max(0, loop.stroke_work_j * pressureScale),
    peak_pressure_mmhg: Math.max(...pressure),
    ef_pct: ((scenarioEdv - scenarioEsv) / scenarioEdv) * 100,
    loop_area_index: loop.loop_area_index == null ? undefined : loop.loop_area_index * pressureScale,
    simulation_label: "M4 hypothetical scenario",
  };
}

export function scenarioPvLoop(result: ScenarioResult, baselineVisualization: SimulationVisualization | null | undefined): PVLoopData | null {
  const loop = baselineVisualization?.pv_loop;
  if (!loop) return null;
  const baseline = result.baseline.state.measurements;
  const scenario = result.scenario.state.measurements;
  const edv = (value: typeof baseline.edv_ml) => value?.value ?? null;
  const esv = (value: typeof baseline.esv_ml) => value?.value ?? null;
  const baselineEdv = edv(baseline.edv_ml);
  const baselineEsv = esv(baseline.esv_ml);
  const scenarioEdv = edv(scenario.edv_ml);
  const scenarioEsv = esv(scenario.esv_ml);
  if ([baselineEdv, baselineEsv, scenarioEdv, scenarioEsv].some((value) => value == null || !Number.isFinite(value))) return null;
  return scaleLoop(loop, baselineEdv!, baselineEsv!, scenarioEdv!, scenarioEsv!);
}
