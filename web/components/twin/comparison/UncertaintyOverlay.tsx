"use client";

import type { ParameterUncertaintyImpact } from "@/types/missing-piece";

type Props = {
  impacts: ParameterUncertaintyImpact[];
  visible?: boolean;
};

/** Scalar uncertainty annotation for the split-heart inspector.
 *
 * This intentionally does not deform the 3D mesh: M5.5 provides scalar
 * distributions, not pointwise geometry. It is an honest handoff layer until
 * canonical regional/mesh uncertainty exists.
 */
export function UncertaintyOverlay({ impacts, visible = true }: Props) {
  if (!visible) return null;
  return (
    <aside className="rounded border border-amber-300/30 bg-amber-300/5 p-2 text-xs text-white" aria-label="Scalar uncertainty overlay">
      <p className="font-semibold uppercase tracking-[.12em] text-amber-200">Scalar uncertainty overlay</p>
      <p className="mt-1 text-white/60">Model-proxy impact annotations; no geometric uncertainty is inferred.</p>
      {impacts.length ? (
        <ul className="mt-2 space-y-1">
          {impacts.slice(0, 3).map((impact) => (
            <li key={`${impact.parameter_id}:${impact.metric_id}`} className="flex justify-between gap-2">
              <span>{impact.parameter_id}</span>
              <span className="tabular-nums text-amber-100">heuristic {impact.impact_score.toFixed(3)}</span>
            </li>
          ))}
        </ul>
      ) : <p className="mt-2 text-white/50">No target-specific impact is available.</p>}
    </aside>
  );
}
