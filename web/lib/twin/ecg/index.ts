import type { TwinEvent, TwinProvenance, TwinTimestamp } from "@/lib/twin/time/contracts";

export type ECGSignalKind = "measured" | "extracted" | "simulated" | "missing";

export interface ECGTimelinePoint {
  timestamp: TwinTimestamp;
  kind: ECGSignalKind;
  rhythmLabel?: string | null;
  rrIntervalMs?: number | null;
  qrsDurationMs?: number | null;
  qtcMs?: number | null;
  sampleCount?: number;
  provenance: TwinProvenance[];
}

export function ecgPointFromEvent(event: TwinEvent): ECGTimelinePoint | null {
  if (event.source !== "ecg" || (event.type !== "measurement" && event.type !== "clinical_evidence")) return null;
  const payload = event.payload;
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
  const value = payload as Record<string, unknown>;
  const kind = value.kind;
  if (kind !== "measured" && kind !== "extracted" && kind !== "simulated" && kind !== "missing") return null;
  return {
    timestamp: event.timestamp,
    kind,
    rhythmLabel: typeof value.rhythmLabel === "string" ? value.rhythmLabel : null,
    rrIntervalMs: typeof value.rrIntervalMs === "number" ? value.rrIntervalMs : null,
    qrsDurationMs: typeof value.qrsDurationMs === "number" ? value.qrsDurationMs : null,
    qtcMs: typeof value.qtcMs === "number" ? value.qtcMs : null,
    sampleCount: typeof value.sampleCount === "number" ? value.sampleCount : undefined,
    provenance: [event.provenance],
  };
}

export function sortECGPoints(points: readonly ECGTimelinePoint[]): ECGTimelinePoint[] {
  return points.slice().sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
}
