import { normalizeTwinTimestamp } from "@/lib/twin/time/contracts";
import type { TwinEvent } from "@/lib/twin/time/contracts";

export interface WearableSampleInput {
  id: string;
  timestamp: string;
  heartRateBpm?: number | null;
  systolicBpMmhg?: number | null;
  diastolicBpMmhg?: number | null;
  sourceId: string;
  quality?: number;
}

function finiteInRange(value: number | null | undefined, min: number, max: number): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= min && value <= max;
}

/** Converts one wearable observation into an explicit, non-diagnostic event. */
export function wearableSampleToEvent(sample: WearableSampleInput): TwinEvent {
  if (!sample.id.trim() || !sample.sourceId.trim()) throw new RangeError("Wearable sample requires stable IDs");
  const timestamp = normalizeTwinTimestamp(sample.timestamp);
  if (!finiteInRange(sample.heartRateBpm, 20, 260) && !finiteInRange(sample.systolicBpMmhg, 40, 300) && !finiteInRange(sample.diastolicBpMmhg, 20, 220)) {
    throw new RangeError("Wearable sample has no valid supported measurement");
  }
  const measured = (value: number, unit: string) => ({
    value,
    unit,
    source: "wearable" as const,
    source_file_id: sample.sourceId,
    confidence: sample.quality ?? 0.8,
    method: "validated wearable adapter",
    evidence: `Wearable sample ${sample.id}`,
  });
  const updates: Array<{ path: string; value: unknown; unit: string }> = [];
  if (finiteInRange(sample.heartRateBpm, 20, 260)) updates.push({ path: "measurements.heart_rate_bpm", value: measured(sample.heartRateBpm, "bpm"), unit: "bpm" });
  if (finiteInRange(sample.systolicBpMmhg, 40, 300)) updates.push({ path: "measurements.systolic_bp_mmhg", value: measured(sample.systolicBpMmhg, "mmHg"), unit: "mmHg" });
  if (finiteInRange(sample.diastolicBpMmhg, 20, 220)) updates.push({ path: "measurements.diastolic_bp_mmhg", value: measured(sample.diastolicBpMmhg, "mmHg"), unit: "mmHg" });
  return {
    id: sample.id,
    timestamp,
    type: "wearable_sample",
    source: "wearable",
    payload: { updates, sourceId: sample.sourceId },
    provenance: {
      source: "wearable",
      sourceId: sample.sourceId,
      method: "validated wearable adapter",
      confidence: sample.quality,
      evidenceIds: [sample.id],
      note: "Wearable observation; not a diagnosis",
    },
  };
}
