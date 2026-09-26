"use client";

import { M4_CAUSAL_GRAPH } from "@/lib/twin/scenario/propagation";
import type { CausalPropagationResult } from "@/lib/twin/scenario/causal";

export function CausalGraph({ propagation }: { propagation: CausalPropagationResult | null }) {
  const delta = new Map(propagation?.deltas.map((item) => [item.nodeId, item]) ?? []);
  const labels = new Map(M4_CAUSAL_GRAPH.nodes.map((node) => [node.id, node.label]));
  return (
    <div aria-label="Causal propagation graph" className="rounded border border-[var(--ht-line)] bg-surface-2 p-2.5">
      <div className="mb-2 flex items-center justify-between">
        <span className="ht-eyebrow">Causal chain</span>
        <span className="text-[0.62rem] text-muted">deterministic · {M4_CAUSAL_GRAPH.version}</span>
      </div>
      {propagation ? <div className="space-y-1.5 text-[0.68rem]">
        {propagation.paths.map((path) => (
          <div key={path.id} className="flex flex-wrap items-center gap-1.5">
            {path.nodeIds.map((nodeId, index) => {
              const item = delta.get(nodeId);
              const changed = item?.delta != null && Math.abs(item.delta) > 0.0001;
              return <span key={`${path.id}-${nodeId}`} className="flex items-center gap-1.5">
                <span className={`rounded border px-2 py-1 ${changed ? "border-accent-bright bg-accent/10 text-ink" : "border-[var(--ht-line)] text-muted"}`}>
                  <span className="block font-medium">{labels.get(nodeId) ?? nodeId}</span>
                  {item ? <span className="ht-mono text-[0.6rem]">{item.delta! >= 0 ? "+" : ""}{item.delta!.toFixed(2)} {item.unit}</span> : null}
                </span>
                {index < path.nodeIds.length - 1 ? <span aria-hidden className="text-muted">→</span> : null}
              </span>;
            })}
          </div>
        ))}
        <ol className="sr-only" aria-label="Causal relationships">
          {propagation.paths.map((path) => <li key={`accessible-${path.id}`}>{path.nodeIds.map((nodeId) => labels.get(nodeId) ?? nodeId).join(" affects ")}</li>)}
        </ol>
      </div> : <p className="text-[0.68rem] text-muted">Run Experiment to reveal causal paths.</p>}
      {propagation?.warnings[0] ? <p className="mt-2 text-[0.62rem] text-muted">{propagation.warnings[0]}</p> : null}
    </div>
  );
}
