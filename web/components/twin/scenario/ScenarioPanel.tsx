"use client";

import { Flask } from "@phosphor-icons/react";
import { CausalGraph } from "@/components/twin/scenario/CausalGraph";
import { ParameterControls } from "@/components/twin/scenario/ParameterControls";
import { ScenarioInspector } from "@/components/twin/scenario/ScenarioInspector";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/Panel";
import { useScenario } from "@/lib/twin/scenario/useScenario";
import { traceFromPropagation } from "@/lib/twin/scenario/trace";
import { useState } from "react";
import { PlausibleTwinsPanel } from "@/components/twin/ensemble/PlausibleTwinsPanel";

export function ScenarioPanel() {
  const scenario = useScenario();
  const [statusMessage, setStatusMessage] = useState("No hypothetical branch computed.");
  const propagation = scenario.result?.causal ?? null;
  const trace = propagation ? traceFromPropagation(propagation) : [];

  return (
    <Panel className="border-t-2 border-[var(--ht-line-strong)] bg-[var(--ht-surface-1)]" raised>
      <PanelHeader icon={Flask} title="Causal Physiology Explorer" accent="accent" />
      <PanelBody>
        <div className="mb-2 rounded border border-accent-bright/40 bg-accent/10 px-2.5 py-2">
          <p className="text-[0.68rem] font-semibold tracking-[0.08em] text-accent-bright">HYPOTHETICAL SIMULATION</p>
          <p className="mt-1 text-[0.68rem] leading-relaxed text-muted">Fork a selected observed snapshot and explore bounded deterministic relationships. Observed history is unchanged.</p>
        </div>
        {!scenario.isAvailable || !scenario.parameters ? (
          <p className="py-4 text-xs text-muted">Select an observed snapshot to begin an experiment.</p>
        ) : (
          <>
            <ParameterControls
              values={scenario.parameters}
              baseline={scenario.baseline}
              onChange={(key, value) => {
                const error = scenario.setParameter(key, value);
                if (error) setStatusMessage(error);
                else setStatusMessage("Parameter updated; run Experiment to recompute the hypothetical branch.");
                return error;
              }}
            />
            <div className="mt-2 flex flex-wrap gap-1.5">
              <button type="button" className="ht-btn ht-btn-primary min-h-8 px-2.5 text-xs" onClick={() => { scenario.experiment(); setStatusMessage("Hypothetical branch computed from the selected observed snapshot."); }}>Experiment</button>
              <button type="button" className="ht-btn ht-btn-secondary min-h-8 px-2.5 text-xs" onClick={() => { scenario.reset(); setStatusMessage("Scenario reset to the observed baseline."); }}>Reset</button>
              <button type="button" className="ht-btn ht-btn-ghost min-h-8 px-2 text-xs" onClick={() => { scenario.undo(); setStatusMessage("Undid the last hypothetical change."); }} disabled={scenario.history.past.length === 0}>Undo</button>
              <button type="button" className="ht-btn ht-btn-ghost min-h-8 px-2 text-xs" onClick={() => { scenario.redo(); setStatusMessage("Redid the hypothetical change."); }} disabled={scenario.history.future.length === 0}>Redo</button>
            </div>
            <p role="status" aria-live="polite" className="mt-2 text-[0.62rem] text-muted">{statusMessage}</p>
            {scenario.result ? <ScenarioInspector result={scenario.result} /> : <p className="mt-3 text-[0.68rem] text-muted">Adjust a control, then run Experiment to compute the causal branch.</p>}
            <CausalGraph propagation={propagation} />
            {trace.length > 0 ? <p className="mt-2 text-[0.62rem] text-muted">{trace.filter((step) => step.delta !== null && Math.abs(step.delta) > 0.0001).length} causal values changed from the observed origin.</p> : null}
            <PlausibleTwinsPanel />
          </>
        )}
      </PanelBody>
    </Panel>
  );
}
