"use client";

import { Flask } from "@phosphor-icons/react";
import { useState } from "react";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/Panel";
import { api } from "@/lib/api";
import { useScenario } from "@/lib/twin/scenario/useScenario";
import type { ShadowTrialMetricId, ShadowTrialResponse } from "@/types/shadow-trial";
import { useDualBeatStore } from "@/lib/store";
import { useComparisonStore } from "@/lib/twin/comparison/store";

const METRICS: ShadowTrialMetricId[] = [
  "ejection_fraction_pct",
  "stroke_volume_ml",
  "cardiac_output_l_min",
  "heart_rate_bpm",
  "map_mmhg",
];

function label(metric: string): string {
  return metric.replaceAll("_", " ").replace("pct", "%");
}

function displayUnit(unit: string): string {
  return unit === "percentage_points" ? "percentage points" : unit;
}

function format(value: number | null | undefined, unit = ""): string {
  const shownUnit = displayUnit(unit);
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(unit === "L/min" ? 2 : 1)} ${shownUnit}` : "unavailable";
}

function DistributionCard({ distribution }: { distribution: ShadowTrialResponse["effect_distributions"][number] }) {
  const low = distribution.quantiles.q05;
  const high = distribution.quantiles.q95;
  const span = typeof low === "number" && typeof high === "number" ? Math.max(Math.abs(low), Math.abs(high), distribution.neutral_tolerance) : 1;
  const width = typeof low === "number" && typeof high === "number" ? Math.max(5, Math.min(100, ((high - low) / (2 * span)) * 100)) : 5;
  return (
    <li className="border-t border-[var(--ht-line)] px-2.5 py-2 first:border-t-0">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-[0.68rem] font-medium text-ink">Δ {label(distribution.metric_id)}</span>
        <span className="ht-mono text-[0.62rem] text-muted">median {format(distribution.median_delta, distribution.unit)}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[var(--ht-line)]" aria-hidden="true">
        <div className="h-full rounded-full bg-[var(--ht-accent)]" style={{ width: `${width}%` }} />
      </div>
      <p className="mt-1 text-[0.6rem] text-muted">
        5th–95th percentile across valid paired plausible twins: {format(low, distribution.unit)}–{format(high, distribution.unit)}.
      </p>
      <p className="mt-1 text-[0.6rem] text-muted">Positive {distribution.positive_count} · near-zero {distribution.neutral_count} · negative {distribution.negative_count}; descriptive simulation categories only.</p>
    </li>
  );
}

function PairInspector({ trial, onCompare }: { trial: ShadowTrialResponse; onCompare: (sampleId: string) => void }) {
  const [selectedId, setSelectedId] = useState(trial.paired_results[0]?.sample_id ?? "");
  const pair = trial.paired_results.find((candidate) => candidate.sample_id === selectedId) ?? trial.paired_results[0];
  if (!pair) return null;
  const value = (state: typeof pair.baseline_state, key: "ejection_fraction_pct" | "stroke_volume_ml" | "cardiac_output_l_min") => state.measurements[key]?.value;
  return (
    <section aria-labelledby="shadow-pair-title" className="mt-3 border border-[var(--ht-line)] p-2.5">
      <h3 id="shadow-pair-title" className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-signal-bright">Same plausible twin — paired inspection</h3>
      <label className="mt-2 block text-[0.62rem] text-muted">
        Select pair
        <select value={pair?.sample_id ?? ""} onChange={(event) => setSelectedId(event.target.value)} className="mt-1 block min-h-8 w-full border border-[var(--ht-line)] bg-[var(--ht-surface-2)] px-2 text-xs text-ink">
          {trial.paired_results.map((candidate) => <option key={candidate.sample_id} value={candidate.sample_id}>{candidate.sample_id}{candidate.valid ? " · valid" : " · invalid"}</option>)}
        </select>
      </label>
      {pair.valid ? <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {["baseline", "scenario"].map((mode) => {
          const state = mode === "baseline" ? pair.baseline_state : pair.scenario_state;
          return <div key={mode} className="border border-[var(--ht-line)] px-2 py-2"><p className="text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-ink-2">{mode}</p><dl className="mt-1 space-y-1 text-[0.62rem] text-muted"><div className="flex justify-between gap-2"><dt>EF</dt><dd className="ht-mono text-ink-2">{format(value(state, "ejection_fraction_pct"), "%")}</dd></div><div className="flex justify-between gap-2"><dt>SV</dt><dd className="ht-mono text-ink-2">{format(value(state, "stroke_volume_ml"), "mL")}</dd></div><div className="flex justify-between gap-2"><dt>CO</dt><dd className="ht-mono text-ink-2">{format(value(state, "cardiac_output_l_min"), "L/min")}</dd></div></dl></div>;
        })}
      </div> : <p className="mt-2 border border-warn/50 bg-warn/10 px-2 py-2 text-[0.62rem] text-warn">Scalar comparison unavailable for this invalid pair.</p>}
      <p className="mt-2 text-[0.62rem] text-muted">Pair ID: {pair.sample_id} ↔ {pair.scenario_twin_id}. The scenario reuses this twin&apos;s stored parameters; no new draw is made.</p>
      {pair.valid ? <button type="button" className="ht-btn ht-btn-primary mt-2 min-h-8 px-2.5 text-xs" onClick={() => onCompare(pair.sample_id)}>Compare this pair</button> : null}
      {!pair.valid ? <p role="alert" className="mt-1 text-[0.62rem] text-warn">Invalid pair retained: {pair.rejection_reasons.join("; ")}</p> : null}
    </section>
  );
}

export function ShadowTrialPanel() {
  const scenario = useScenario();
  const referenceVisualization = useDualBeatStore((state) => state.visualization);
  const openComparison = useComparisonStore((state) => state.open);
  const closeComparison = useComparisonStore((state) => state.close);
  const [trialRun, setTrialRun] = useState<{ response: ShadowTrialResponse; ensembleId: string; scenarioId: string } | null>(null);
  const [status, setStatus] = useState("Choose a baseline ensemble and run a bounded hypothetical experiment.");
  const [loading, setLoading] = useState(false);
  const currentEnsembleId = scenario.ensemble?.id ?? "";
  const currentScenarioId = scenario.result?.definition.id ?? "";
  const trial = trialRun && trialRun.ensembleId === currentEnsembleId && trialRun.scenarioId === currentScenarioId ? trialRun.response : null;

  const run = async () => {
    if (!scenario.ensemble || !scenario.result || !scenario.selectedSnapshot) {
      setStatus("Generate plausible twins and run the hypothetical Experiment first.");
      return;
    }
    setLoading(true);
    try {
      closeComparison();
      const definition = scenario.result.definition;
      const response = await api.createShadowTrial({
        baseline_ensemble_id: scenario.ensemble.id,
        scenario: {
          id: definition.id,
          label: definition.label,
          description: definition.description,
          origin_snapshot_id: scenario.selectedSnapshot.id,
          created_at: definition.createdAt,
          parameters: definition.parameters.map((parameter) => ({
            parameter: parameter.parameter,
            baseline: parameter.baseline,
            value: parameter.value,
            delta: parameter.delta,
            unit: parameter.unit,
          })),
        },
        metrics: METRICS,
      });
      setTrialRun({ response, ensembleId: currentEnsembleId, scenarioId: currentScenarioId });
      setStatus(`${response.valid_pairs} valid paired simulations; ${response.invalid_pairs} invalid pair(s) retained.`);
    } catch (error) {
      setStatus(error instanceof Error ? `Unable to run Shadow Trial: ${error.message}` : "Unable to run Shadow Trial.");
      setTrialRun(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Panel className="border-t-2 border-[var(--ht-line-strong)] bg-[var(--ht-surface-1)]" raised>
      <PanelHeader icon={Flask} title="Shadow Trial" accent="accent" />
      <PanelBody>
        <div className="mb-2 rounded border border-accent-bright/40 bg-accent/10 px-2.5 py-2">
          <p className="text-[0.68rem] font-semibold tracking-[0.08em] text-accent-bright">PAIRED HYPOTHETICAL EXPERIMENT</p>
          <p className="mt-1 text-[0.68rem] leading-relaxed text-muted">The same bounded scenario is applied to every stored plausible twin and compared with that same twin&apos;s baseline state.</p>
        </div>
        <button type="button" className="ht-btn ht-btn-primary min-h-8 px-2.5 text-xs" onClick={run} disabled={loading || !scenario.ensemble}>{loading ? "Running Shadow Trial…" : "Run Shadow Trial"}</button>
        <p role={status.startsWith("Unable") ? "alert" : "status"} aria-live="polite" className="mt-2 text-[0.62rem] text-muted">{status}</p>
        {trial ? (
          <>
            <div className="mt-2 grid grid-cols-3 gap-1.5 text-center text-[0.62rem]"><div className="border border-[var(--ht-line)] px-1.5 py-2"><p className="text-muted">baseline twins</p><p className="mt-1 ht-mono text-ink">{trial.requested_pairs}</p></div><div className="border border-[var(--ht-line)] px-1.5 py-2"><p className="text-muted">valid pairs</p><p className="mt-1 ht-mono text-signal-bright">{trial.valid_pairs}</p></div><div className="border border-[var(--ht-line)] px-1.5 py-2"><p className="text-muted">invalid pairs</p><p className="mt-1 ht-mono text-warn">{trial.invalid_pairs}</p></div></div>
            {trial.status === "failed" ? <p role="alert" className="mt-3 border border-warn/50 bg-warn/10 px-2.5 py-2 text-[0.65rem] text-warn">No valid paired outcomes were available. The retained invalid pairs are shown for inspection; no effect summary is presented.</p> : null}
            {trial.valid_pairs > 0 && trial.effect_distributions.length > 0 ? <ul className="mt-3 border border-[var(--ht-line)]" aria-label="Paired simulated effect distributions">{trial.effect_distributions.map((distribution) => <DistributionCard key={distribution.metric_id} distribution={distribution} />)}</ul> : <p className="mt-3 border border-[var(--ht-line)] px-2.5 py-2 text-[0.65rem] text-muted">Effect distributions are unavailable until at least one pair passes validation.</p>}
            <PairInspector trial={trial} onCompare={(sampleId) => { if (referenceVisualization) openComparison(trial, sampleId, referenceVisualization); }} />
            <div className="mt-3 border border-[var(--ht-line)] px-2.5 py-2 text-[0.62rem] text-muted"><p className="font-semibold text-ink-2">PV comparison boundary</p><p className="mt-1">M5.5 does not return pointwise PV samples. This M6 surface does not fabricate a PV uncertainty envelope; the baseline shape remains held until canonical pointwise data exists.</p></div>
            <details className="mt-2 text-[0.6rem] text-muted"><summary className="cursor-pointer text-ink-2">Provenance and assumptions</summary><ul className="mt-1 list-disc pl-4"><li>Trial {trial.id}</li><li>Baseline ensemble {trial.baseline_ensemble_id}</li><li>Same-sample pairing; no scenario resampling</li>{trial.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></details>
            <p className="mt-2 text-[0.6rem] text-warn">HYPOTHETICAL SIMULATION · {trial.provenance.origin_quality === "synthetic" ? "SYNTHETIC ORIGIN · " : ""}not clinical advice or treatment guidance</p>
          </>
        ) : null}
      </PanelBody>
    </Panel>
  );
}
