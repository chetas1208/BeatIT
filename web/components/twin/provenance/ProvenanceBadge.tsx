"use client";

import type { TwinSnapshot } from "@/lib/twin/time/contracts";
import { lineageForSnapshot } from "@/lib/twin/provenance";

export function ProvenanceBadge({ snapshot }: { snapshot: TwinSnapshot | null }) {
  const lineage = lineageForSnapshot(snapshot);
  return (
    <span className="ht-chip" title={lineage.evidenceIds.join(", ") || "No evidence IDs"}>
      {lineage.summary}
    </span>
  );
}
