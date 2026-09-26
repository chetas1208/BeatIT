import type { CardiacTwinState, MeasuredValue, SimulationVisualization } from "@/types/heart";
import { reconstructTimeline } from "@/lib/twin/snapshots";
import type { TwinEvent, TwinTimeline, TwinTimestamp } from "@/lib/twin/time/contracts";

const DAY_MS = 24 * 60 * 60 * 1000;

function replayValue(value: number, unit: string): MeasuredValue {
  return {
    value,
    unit,
    source: "derived",
    source_file_id: "beatit-replay-m3",
    confidence: 0.9,
    method: "deterministic synthetic replay",
    evidence: "DEMO STREAM; synthetic value",
  };
}

function event(
  id: string,
  timestamp: string,
  path: string,
  value: unknown,
  unit: string,
): TwinEvent {
  return {
    id,
    timestamp,
    type: "measurement",
    source: "synthetic_replay",
    payload: { path, value, unit },
    provenance: {
      source: "synthetic_replay",
      sourceId: "beatit-replay-m3",
      method: "deterministic fixture",
      confidence: 0.9,
      evidenceIds: [id],
      note: "REPLAY / DEMO STREAM; not a live medical-device feed",
    },
  };
}

/** Stable, synthetic events for the M3 hackathon scrub demo. */
export function createReplayEvents(startTime: TwinTimestamp): TwinEvent[] {
  const start = Date.parse(startTime);
  if (!Number.isFinite(start)) throw new RangeError("Replay startTime must be a valid timestamp");
  const at = (days: number) => new Date(start + days * DAY_MS).toISOString();
  return [
    event("replay-ef-baseline", at(0.25), "measurements.ejection_fraction_pct", replayValue(48, "%"), "%"),
    event("replay-heart-rate", at(0.75), "measurements.heart_rate_bpm", replayValue(78, "bpm"), "bpm"),
    event("replay-ef-followup", at(1.25), "measurements.ejection_fraction_pct", replayValue(54, "%"), "%"),
    event("replay-scar-followup", at(1.75), "tissue_state.scar_fraction", replayValue(0.1, "fraction"), "fraction"),
    event("replay-ef-live", at(2), "measurements.ejection_fraction_pct", replayValue(57, "%"), "%"),
  ];
}

export function createReplayTimeline(
  initialState: CardiacTwinState,
  initialVisualization?: SimulationVisualization,
): TwinTimeline {
  return reconstructTimeline(initialState, createReplayEvents(initialState.created_at), {
    patientId: initialState.case_id,
    initialVisualization,
    initialQuality: "synthetic",
    initialProvenance: [{
      source: "synthetic_replay",
      sourceId: "beatit-replay-m3",
      method: "deterministic fixture",
      note: "REPLAY / DEMO STREAM",
    }],
  });
}
