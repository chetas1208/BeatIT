"use client";

import { useMemo, useState } from "react";
import { ChartLineUp } from "@phosphor-icons/react";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/Panel";
import { useScenario } from "@/lib/twin/scenario/useScenario";
import type { OutputDistribution, TwinEnsemble } from "@/lib/twin/ensemble/contracts";
import { pvUncertaintyEnvelope } from "@/lib/twin/ensemble/pvEnvelope";
import { EnsembleUncertaintyInspector } from "@/components/twin/ensemble/EnsembleUncertaintyInspector";

function format(value: number, unit: string): string {
  return `${value.toFixed(unit === "%" ? 1 : 2)} ${unit}`;
}

function DistributionRow({ distribution }: { distribution: OutputDistribution }) {
  return (
    <li className="border-t border-[var(--ht-line)] px-2.5 py-2 first:border-t-0">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[0.68rem] font-medium text-ink">{distribution.metricId.replaceAll("_", " ")}</span>
        <span className="ht-mono text-[0.62rem] text-muted">median {format(distribution.median, distribution.unit)}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[var(--ht-line)]" aria-hidden="true">
        <div className="h-full rounded-full bg-[var(--ht-accent)]" style={{ width: `${Math.max(4, Math.min(100, (distribution.quantiles.q95 - distribution.quantiles.q05) / Math.max(0.001, distribution.max - distribution.min) * 100))}%` }} />
      </div>
      <p className="mt-1 text-[0.6rem] text-muted">5th–95th percentile of accepted deterministic simulations: {format(distribution.quantiles.q05, distribution.unit)}–{format(distribution.quantiles.q95, distribution.unit)}</p>
    </li>
  );
}

function chooseRepresentatives(ensemble: TwinEnsemble) {
  const ids = ensemble.representativeIds;
  if (!ids) return { median: null, low: null, high: null };
  const byId = (id: string | null) => id ? ensemble.samples.find((sample) => sample.id === id && sample.valid) ?? null : null;
  return {
    low: byId(ids.low),
    high: byId(ids.high),
    median: byId(ids.median),
  };
}

export function PlausibleTwinsPanel() {
  const scenario = useScenario();
  const [sampleCount, setSampleCount] = useState(100);
  const [status, setStatus] = useState("No plausible-twin ensemble computed.");
  const [loading, setLoading] = useState(false);
  const ensemble = scenario.ensemble;
  const representatives = useMemo(() => ensemble ? chooseRepresentatives(ensemble) : null, [ensemble]);

  const generate = async () => {
    setLoading(true);
    try {
      const next = await scenario.generateEnsemble({ requestedSampleCount: sampleCount, seed: 1208 });
      setStatus(next ? `${next.acceptedSampleCount} accepted; ${next.rejectedSampleCount} rejected. Seed 1208.` : "Select a snapshot with explicit lineage first.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to generate plausible twins.");
    } finally {
      setLoading(false);
    }
  };

  const choose = (label: string, sample: Parameters<typeof scenario.selectEnsembleSample>[0] | null) => {
    scenario.selectEnsembleSample(sample);
    setStatus(sample ? `${label} plausible simulated twin selected.` : "Median plausible simulated twin selected.");
  };

  return (
    <Panel className="border-t-2 border-[var(--ht-line-strong)] bg-[var(--ht-surface-1)]" raised>
      <PanelHeader icon={ChartLineUp} title="Plausible Twins" accent="signal" />
      <PanelBody>
        <div className="mb-2 rounded border border-signal/40 bg-signal/10 px-2.5 py-2">
          <p className="text-[0.68rem] font-semibold tracking-[0.08em] text-signal">UNCERTAINTY MODE</p>
          <p className="mt-1 text-[0.68rem] leading-relaxed text-muted">Uncertainty is sampled from inputs and propagated through the deterministic physiology engine. It is not AI confidence or a clinical probability.</p>
        </div>
        {!scenario.isAvailable ? <p className="py-3 text-xs text-muted">Select a snapshot with explicit lineage to generate plausible twins.</p> : (
          <>
            <div className="flex flex-wrap items-end gap-2" aria-busy={loading}>
              <label className="text-[0.62rem] text-muted">
                Sample count
                <select value={sampleCount} onChange={(event) => setSampleCount(Number(event.target.value))} className="mt-1 block min-h-8 border border-[var(--ht-line)] bg-[var(--ht-surface-2)] px-2 text-xs text-ink">
                  {[50, 100, 250, 500, 1000].map((count) => <option key={count} value={count}>{count}</option>)}
                </select>
              </label>
              <button type="button" className="ht-btn ht-btn-primary min-h-8 px-2.5 text-xs" onClick={generate} disabled={loading}>{loading ? "Generating…" : "Generate twins"}</button>
            </div>
            <p role={status.startsWith("Unable") ? "alert" : "status"} aria-live={status.startsWith("Unable") ? "assertive" : "polite"} className="mt-2 text-[0.62rem] text-muted">{status}</p>
            {ensemble ? (
              <>
                <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-3">
                  {(["median", "low", "high"] as const).map((label) => {
                    const sample = representatives?.[label] ?? null;
                    const metric = ensemble.distributions.find((distribution) => distribution.metricId === "ejection_fraction_pct");
                    const sampleEf = sample?.state.measurements.ejection_fraction_pct?.value;
                    const displayLabel = label === "low" ? "lowest accepted" : label === "high" ? "highest accepted" : "median-nearest";
                    const labelText = `${displayLabel} plausible simulated twin${typeof sampleEf === "number" ? `, EF ${Math.round(sampleEf)}%` : ""}`;
                    return <button key={label} type="button" aria-label={labelText} aria-pressed={sample?.id === scenario.selectedEnsembleSample?.id} className="ht-btn ht-btn-secondary min-h-8 px-1 text-[0.62rem]" onClick={() => choose(displayLabel, sample)} disabled={!sample}>{displayLabel}{metric ? ` · ${Math.round(sampleEf ?? metric.median)}%` : ""}</button>;
                  })}
                </div>
                <ul className="mt-2 border border-[var(--ht-line)]" aria-label="Plausible output distributions">
                  {ensemble.distributions.map((distribution) => <DistributionRow key={distribution.metricId} distribution={distribution} />)}
                </ul>
                <p className="mt-2 text-[0.6rem] text-muted">Origin {ensemble.originSnapshotId} · seed {ensemble.seed} · {ensemble.acceptedSampleCount}/{ensemble.requestedSampleCount} accepted</p>
                {(() => {
                  const envelope = pvUncertaintyEnvelope(ensemble);
                  return (
                    <div className="mt-2 border border-[var(--ht-line)] px-2 py-1.5 text-[0.6rem] text-muted" aria-label="Scalar ejection fraction and stroke volume uncertainty">
                      <p className="font-semibold text-ink">Scalar EF/SV uncertainty</p>
                      <p className="mt-1">EF {envelope.ejectionFraction ? `${format(envelope.ejectionFraction.quantiles.q05, envelope.ejectionFraction.unit)}–${format(envelope.ejectionFraction.quantiles.q95, envelope.ejectionFraction.unit)}` : "unavailable"} · SV {envelope.strokeVolume ? `${format(envelope.strokeVolume.quantiles.q05, envelope.strokeVolume.unit)}–${format(envelope.strokeVolume.quantiles.q95, envelope.strokeVolume.unit)}` : "unavailable"}</p>
                      <p className="mt-1">{envelope.limitation}</p>
                    </div>
                  );
                })()}
                <EnsembleUncertaintyInspector ensemble={ensemble} />
                <details className="mt-2 text-[0.6rem] text-muted">
                  <summary className="cursor-pointer text-ink-2">Assumptions and warnings</summary>
                  <ul className="mt-1 list-disc pl-4">{[...ensemble.provenance.assumptions, ...ensemble.warnings].map((warning) => <li key={warning}>{warning}</li>)}</ul>
                </details>
                <p className="mt-1 text-[0.6rem] text-warn">PLAUSIBLE SIMULATED TWIN · baseline PV shape held; {ensemble.provenance.originQuality === "synthetic" ? "synthetic replay origin · " : ""}5th–95th percentile · educational only</p>
              </>
            ) : null}
          </>
        )}
      </PanelBody>
    </Panel>
  );
}
