"use client";

import type { EvidenceConstraint, EvidenceValueEstimate } from "@/types/missing-piece";

type Props = { ranking: EvidenceValueEstimate[]; constraints: EvidenceConstraint[] };

export function EvidenceMap({ ranking, constraints }: Props) {
  const rationaleByType = new Map(constraints.map((item) => [item.evidence_type, item.rationale]));
  return (
    <div className="space-y-2" aria-label="Evidence priority ranking">
      {ranking.map((item, index) => (
        <article key={item.evidence_type} className="rounded-lg border border-white/10 bg-white/[.03] p-3">
          <div className="flex items-center justify-between gap-3">
            <h4 className="text-sm font-medium text-white">{index + 1}. {item.evidence_type}</h4>
            <span className="text-xs tabular-nums text-cyan-200">Priority {item.ranking_score.toFixed(3)}</span>
          </div>
          <p className="mt-1 text-xs text-white/60">Constrains: {item.constrained_parameters.join(", ")}</p>
          <p className="mt-1 text-xs text-white/50">{rationaleByType.get(item.evidence_type) ?? "No additional rationale recorded."}</p>
        </article>
      ))}
    </div>
  );
}
