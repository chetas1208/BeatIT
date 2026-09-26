import type { TwinEvent, TwinProvenance, TwinSnapshot } from "@/lib/twin/time/contracts";

export interface ProvenanceLineage {
  evidenceIds: string[];
  sources: TwinProvenance[];
  summary: string;
}

export function lineageForSnapshot(snapshot: TwinSnapshot | null): ProvenanceLineage {
  if (!snapshot) return { evidenceIds: [], sources: [], summary: "No snapshot selected" };
  const sourceLabels = [...new Set(snapshot.provenance.map((item) => item.source))];
  return {
    evidenceIds: snapshot.evidenceIds.slice(),
    sources: snapshot.provenance.map((item) => ({ ...item, evidenceIds: item.evidenceIds?.slice() })),
    summary: `${snapshot.quality} snapshot · ${sourceLabels.join(", ") || "unknown source"}`,
  };
}

export function lineageForEvent(event: TwinEvent): ProvenanceLineage {
  return {
    evidenceIds: [event.id, ...(event.provenance.evidenceIds ?? [])].filter((id, index, ids) => ids.indexOf(id) === index),
    sources: [{ ...event.provenance, evidenceIds: event.provenance.evidenceIds?.slice() }],
    summary: `${event.type} · ${event.source}`,
  };
}
