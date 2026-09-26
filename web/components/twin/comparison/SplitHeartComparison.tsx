"use client";

import { ArrowLeft, LinkSimple, Pause, Play, SplitHorizontal } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { HeartTwinInstance } from "@/components/heart/HeartScene";
import { ComparisonMetrics } from "@/components/twin/comparison/ComparisonMetrics";
import { UncertaintyOverlay } from "@/components/twin/comparison/UncertaintyOverlay";
import { advanceComparisonClock, createComparisonClock, pauseComparisonClock, playComparisonClock, resyncComparisonClock, seekComparisonClock, setComparisonClockHeartRates, setComparisonClockMode, type ComparisonClockState } from "@/lib/twin/comparison/clock";
import { buildComparisonDeltas } from "@/lib/twin/comparison/differences";
import { comparisonVisualization } from "@/lib/twin/comparison/visualization";
import { projectPVCursor } from "@/lib/twin/comparison/pv";
import type { ShadowTrialPair } from "@/types/shadow-trial";
import type { ParameterUncertaintyImpact } from "@/types/missing-piece";
import type { SimulationVisualization } from "@/types/heart";

interface SplitHeartComparisonProps {
  pair: ShadowTrialPair;
  templateVisualization: SimulationVisualization;
  scenarioLabel: string;
  originLabel: string;
  onClose: () => void;
  uncertaintyImpacts?: ParameterUncertaintyImpact[];
}

function metricValue(pair: ShadowTrialPair, side: "baseline" | "scenario", key: keyof ShadowTrialPair["baseline_state"]["measurements"]): number | null {
  const state = side === "baseline" ? pair.baseline_state : pair.scenario_state;
  const value = state.measurements[key]?.value;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function plotPoints(values: readonly number[], min: number, max: number): string {
  const span = Math.max(1e-9, max - min);
  return values.map((value, index) => `${8 + (index / Math.max(1, values.length - 1)) * 184},${88 - ((value - min) / span) * 76}`).join(" ");
}

function PVLoop({ label, visualization, phase }: { label: string; visualization: SimulationVisualization; phase: number }) {
  const volumes = visualization.pv_loop.volume_ml;
  const pressures = visualization.pv_loop.pressure_mmhg;
  if (volumes.length < 2 || pressures.length < 2) return <div className="grid min-h-28 place-items-center border border-dashed border-[var(--ht-line)] text-[0.62rem] text-muted">{label} PV unavailable</div>;
  const volumeMin = Math.min(...volumes);
  const volumeMax = Math.max(...volumes);
  const pressureMin = Math.min(...pressures);
  const pressureMax = Math.max(...pressures);
  const projected = projectPVCursor(visualization.pv_loop, phase);
  const index = projected.cursorIndex ?? 0;
  const x = 8 + (index / Math.max(1, volumes.length - 1)) * 184;
  const y = 88 - ((pressures[index]! - pressureMin) / Math.max(1e-9, pressureMax - pressureMin)) * 76;
  return <figure className="border border-[var(--ht-line)] p-2"><figcaption className="flex justify-between text-[0.62rem]"><span className="font-medium text-ink-2">{label} PV loop</span><span className="text-muted">SIMULATED · shape held</span></figcaption><svg className="mt-1 h-28 w-full" viewBox="0 0 200 96" role="img" aria-label={`${label} simulated pressure-volume loop at ${(phase * 100).toFixed(0)} percent phase`}><polyline points={plotPoints(volumes, volumeMin, volumeMax)} fill="none" stroke="var(--ht-signal)" strokeWidth="2" /><circle cx={x} cy={y} r="3" fill="var(--ht-accent-bright)" /><text x="8" y="95" fill="var(--ht-muted)" fontSize="5">volume</text><text x="2" y="8" fill="var(--ht-muted)" fontSize="5">pressure</text></svg></figure>;
}

export function SplitHeartComparison({ pair, templateVisualization, scenarioLabel, originLabel, onClose, uncertaintyImpacts = [] }: SplitHeartComparisonProps) {
  const baselineHeartRate = metricValue(pair, "baseline", "heart_rate_bpm") ?? templateVisualization.summary.heart_rate_bpm;
  const scenarioHeartRate = metricValue(pair, "scenario", "heart_rate_bpm") ?? baselineHeartRate;
  const [clock, setClock] = useState<ComparisonClockState>(() => createComparisonClock({ baselineHeartRateBpm: baselineHeartRate, scenarioHeartRateBpm: scenarioHeartRate }, { mode: "phase_locked", playing: true }));
  const [linkedSelection, setLinkedSelection] = useState(true);
  const [differenceOnly, setDifferenceOnly] = useState(false);
  const [baselineSelection, setBaselineSelection] = useState<string | null>(null);
  const [scenarioSelection, setScenarioSelection] = useState<string | null>(null);
  const baselineVisualization = useMemo(() => comparisonVisualization(pair.baseline_state, templateVisualization, "Baseline paired twin"), [pair.baseline_state, templateVisualization]);
  const scenarioVisualization = useMemo(() => comparisonVisualization(pair.scenario_state, templateVisualization, "Counterfactual paired twin"), [pair.scenario_state, templateVisualization]);
  const deltas = useMemo(() => buildComparisonDeltas(pair), [pair]);

  useEffect(() => {
    let frame = 0;
    let previous = performance.now();
    const tick = (now: number) => { const elapsedMs = Math.max(0, now - previous); previous = now; setClock((current) => advanceComparisonClock(setComparisonClockHeartRates(current, { baselineHeartRateBpm: baselineVisualization.summary.heart_rate_bpm, scenarioHeartRateBpm: scenarioVisualization.summary.heart_rate_bpm }), { elapsedMs })); frame = requestAnimationFrame(tick); };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [baselineVisualization.summary.heart_rate_bpm, scenarioVisualization.summary.heart_rate_bpm]);

  const select = useCallback((side: "baseline" | "scenario", componentId: string) => {
    if (linkedSelection) { setBaselineSelection(componentId); setScenarioSelection(componentId); }
    else if (side === "baseline") setBaselineSelection(componentId);
    else setScenarioSelection(componentId);
  }, [linkedSelection]);
  const clear = useCallback((side: "baseline" | "scenario") => {
    if (linkedSelection) { setBaselineSelection(null); setScenarioSelection(null); }
    else if (side === "baseline") setBaselineSelection(null);
    else setScenarioSelection(null);
  }, [linkedSelection]);

  return <section aria-labelledby="split-heart-title" className="mt-3 border-2 border-[var(--ht-line-strong)] bg-[var(--ht-surface-1)]">
    <header className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--ht-line)] px-3 py-3"><div><p className="ht-eyebrow text-accent-bright">BeatIT · Split Heart</p><h3 id="split-heart-title" className="mt-1 text-sm font-semibold text-ink">Baseline vs counterfactual</h3><p className="mt-1 max-w-xl text-[0.68rem] text-muted">One paired Shadow Trial twin, shown before and after: {scenarioLabel}.</p><p className="mt-1 text-[0.6rem] text-faint">Origin {originLabel} · Pair {pair.sample_id} · {pair.baseline_twin_id} → {pair.scenario_twin_id}</p></div><button type="button" className="ht-btn ht-btn-ghost min-h-8 px-2 text-xs" onClick={onClose}><ArrowLeft weight="bold" className="size-3" /> Close compare</button></header>
    <div className="border-b border-[var(--ht-line)] px-3 py-2" role="group" aria-label="Comparison clock controls"><div className="flex flex-wrap items-center gap-2"><span className="ht-chip" data-status="running">{clock.mode === "phase_locked" ? "SYNCED COMPARISON" : "PHYSIOLOGIC RATE"}</span><button type="button" className="ht-btn ht-btn-ghost min-h-8 px-2 text-xs" onClick={() => setClock((current) => current.playing ? pauseComparisonClock(current) : playComparisonClock(current))} aria-label={clock.playing ? "Pause both hearts" : "Play both hearts"}>{clock.playing ? <Pause weight="fill" className="size-3" /> : <Play weight="fill" className="size-3" />}{clock.playing ? "Pause" : "Play"}</button><button type="button" className={`ht-btn min-h-8 px-2 text-xs ${clock.mode === "phase_locked" ? "ht-btn-primary" : "ht-btn-ghost"}`} onClick={() => setClock((current) => setComparisonClockMode(current, "phase_locked"))}>Phase locked</button><button type="button" className={`ht-btn min-h-8 px-2 text-xs ${clock.mode === "physiologic_rate" ? "ht-btn-primary" : "ht-btn-ghost"}`} onClick={() => setClock((current) => setComparisonClockMode(current, "physiologic_rate"))}>True rate</button><button type="button" className="ht-btn ht-btn-ghost min-h-8 px-2 text-xs" onClick={() => setClock((current) => resyncComparisonClock(current))}>Re-sync</button><label className="ml-auto flex min-w-[12rem] flex-1 items-center gap-2 text-[0.62rem] text-muted"><span>DIASTOLE</span><input aria-label="Scrub cardiac phase" type="range" min="0" max="0.999" step="0.001" value={clock.normalizedPhase} onChange={(event) => setClock((current) => seekComparisonClock(current, Number(event.target.value)))} className="min-w-0 flex-1" /><span>SYSTOLE</span></label></div><div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.6rem] text-muted"><span>Baseline <b className="ht-mono text-ink-2">{baselineHeartRate.toFixed(0)} bpm</b> · phase {clock.baselinePhase.toFixed(2)}</span><span>Counterfactual <b className="ht-mono text-ink-2">{scenarioHeartRate.toFixed(0)} bpm</b> · phase {clock.scenarioPhase.toFixed(2)}</span></div></div>
    <div className="grid gap-2 p-2 lg:grid-cols-2"><div className="min-w-0 border border-[var(--ht-line)]"><div className="flex items-center justify-between border-b border-[var(--ht-line)] px-2.5 py-2"><span className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-ink">Baseline</span><span className="ht-mono text-[0.62rem] text-muted">{baselineHeartRate.toFixed(0)} BPM</span></div><div className="h-[22rem]"><HeartTwinInstance instanceId="baseline" state={pair.baseline_state} visualization={baselineVisualization} selectedComponentId={baselineSelection} phaseOverride={clock.baselinePhase} playingOverride={clock.playing} onComponentSelect={(id) => select("baseline", id)} onComponentClear={() => clear("baseline")} /></div></div><div className="min-w-0 border border-[var(--ht-line)]"><div className="flex items-center justify-between border-b border-[var(--ht-line)] px-2.5 py-2"><span className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-ink">Counterfactual</span><span className="ht-mono text-[0.62rem] text-muted">{scenarioHeartRate.toFixed(0)} BPM</span></div><div className="h-[22rem]"><HeartTwinInstance instanceId="counterfactual" state={pair.scenario_state} visualization={scenarioVisualization} selectedComponentId={scenarioSelection} phaseOverride={clock.scenarioPhase} playingOverride={clock.playing} onComponentSelect={(id) => select("scenario", id)} onComponentClear={() => clear("scenario")} /></div></div></div>
    <div className="flex flex-wrap items-center gap-2 border-t border-[var(--ht-line)] px-3 py-2"><button type="button" className={`ht-btn min-h-8 px-2 text-xs ${linkedSelection ? "ht-btn-primary" : "ht-btn-ghost"}`} onClick={() => setLinkedSelection((value) => !value)} aria-pressed={linkedSelection}><LinkSimple weight="bold" className="size-3" /> {linkedSelection ? "Linked selection" : "Independent selection"}</button><button type="button" className={`ht-btn min-h-8 px-2 text-xs ${differenceOnly ? "ht-btn-primary" : "ht-btn-ghost"}`} onClick={() => setDifferenceOnly((value) => !value)} aria-pressed={differenceOnly}><SplitHorizontal weight="bold" className="size-3" /> Show only differences</button>{differenceOnly && deltas.length === 0 ? <span className="text-[0.62rem] text-muted">NO MODELED DIFFERENCE</span> : null}</div>
    <ComparisonMetrics model={{ baselineLabel: "Baseline", scenarioLabel: "Counterfactual", metrics: deltas }} differenceOnly={differenceOnly} description="Values and deltas come from the persisted M6 Shadow Trial pair; no frontend physiology is recomputed." />
    <div className="border-t border-[var(--ht-line)] px-3 py-3"><UncertaintyOverlay impacts={uncertaintyImpacts} /></div>
    <section aria-labelledby="pv-comparison-title" className="border-t border-[var(--ht-line)] px-3 py-3"><h4 id="pv-comparison-title" className="text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-ink">PV comparison</h4><div className="mt-2 grid gap-2 lg:grid-cols-2"><PVLoop label="Baseline" visualization={baselineVisualization} phase={clock.baselinePhase} /><PVLoop label="Counterfactual" visualization={scenarioVisualization} phase={clock.scenarioPhase} /></div><p className="mt-2 text-[0.6rem] text-muted">PV cursors follow the comparison clock. M6 supplies scalar effects, so the source loop shape is held and no pointwise uncertainty envelope is fabricated.</p></section>
    <section aria-labelledby="signal-comparison-title" className="border-t border-[var(--ht-line)] px-3 py-3"><h4 id="signal-comparison-title" className="text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-ink">Electrical / signal context</h4><div className="mt-2 grid gap-2 text-[0.62rem] text-muted sm:grid-cols-2"><p className="border border-[var(--ht-line)] p-2">Baseline · {baselineVisualization.electrophysiology.rhythm_label ?? "rhythm context unavailable"}<br /><span className="text-faint">Simulated timing context; no measured waveform inferred.</span></p><p className="border border-[var(--ht-line)] p-2">Counterfactual · {scenarioVisualization.electrophysiology.rhythm_label ?? "rhythm context unavailable"}<br /><span className="text-faint">Educational signal context only.</span></p></div></section>
    <p className="border-t border-[var(--ht-line)] px-3 py-2 text-[0.6rem] text-warn">HYPOTHETICAL SIMULATION · paired visual projection only · not diagnosis, treatment guidance, or patient-specific mechanics.</p>
  </section>;
}
