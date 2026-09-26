import type { SimulationVisualization } from "@/types/heart";
import type { TwinSnapshot } from "@/lib/twin/time/contracts";

export type PVContextKind = "measured" | "simulated" | "missing";

export interface TemporalPVContext {
  kind: PVContextKind;
  visualization: SimulationVisualization | null;
  timestamp: string;
  label: string;
  evidenceIds: string[];
}

export function pvContextForSnapshot(snapshot: TwinSnapshot | null): TemporalPVContext {
  if (!snapshot?.visualization?.pv_loop) {
    return {
      kind: "missing",
      visualization: null,
      timestamp: snapshot?.timestamp ?? "",
      label: "PV unavailable for this snapshot",
      evidenceIds: snapshot?.evidenceIds.slice() ?? [],
    };
  }
  const label = snapshot.visualization.pv_loop.simulation_label ?? snapshot.visualization.simulation_note;
  return {
    kind: snapshot.quality === "synthetic" ? "simulated" : "simulated",
    visualization: snapshot.visualization,
    timestamp: snapshot.timestamp,
    label: label ? `PV · ${label}` : "PV · selected snapshot",
    evidenceIds: snapshot.evidenceIds.slice(),
  };
}
