"use client";

import { useId } from "react";
import type { TwinSnapshot } from "@/lib/twin/time/contracts";

export interface ScenarioForkProps {
  snapshot: TwinSnapshot;
  onExperiment: (snapshot: TwinSnapshot) => void;
}

/**
 * Starts a hypothetical experiment from an observed snapshot without writing
 * to the observed timeline.
 */
export function ScenarioFork({ snapshot, onExperiment }: ScenarioForkProps) {
  const descriptionId = useId();

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-2">
      <p id={descriptionId} className="text-[0.68rem] text-muted">
        HYPOTHETICAL SIMULATION · Observed history is unchanged.
      </p>
      <button
        type="button"
        className="ht-btn ht-btn-primary min-h-8 px-2.5 text-xs"
        onClick={() => onExperiment(snapshot)}
        aria-describedby={descriptionId}
        aria-label="Experiment from this snapshot (hypothetical simulation)"
      >
        Experiment
      </button>
    </div>
  );
}
