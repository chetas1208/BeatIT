"use client";

import { useId, useRef, useState } from "react";

import { createMissingPiece } from "@/lib/api";
import { shouldApplyMissingPieceResult } from "@/lib/twin/missing-piece/requestIdentity";
import type { MissingPieceResponse } from "@/types/missing-piece";

import { EvidenceMap } from "./EvidenceMap";
import { SensitivityTable } from "./SensitivityTable";

type Props = { ensembleId?: string; initialMetric?: string };

const TARGETS = [
  { value: "stroke_volume_ml", label: "Stroke volume" },
  { value: "ejection_fraction_pct", label: "Ejection fraction" },
  { value: "cardiac_output_l_min", label: "Cardiac output" },
  { value: "heart_rate_bpm", label: "Heart rate" },
] as const;

const DEFAULT_METRIC = TARGETS[0].value;

function metricLabel(metric: string): string {
  return TARGETS.find((target) => target.value === metric)?.label ?? metric;
}

function formatScore(value: number): string {
  return Number.isFinite(value) ? value.toFixed(3) : "Unavailable";
}

export function MissingPiecePanel(props: Props) {
  return <MissingPiecePanelContent key={props.ensembleId ?? "no-ensemble"} {...props} />;
}

function MissingPiecePanelContent({ ensembleId, initialMetric = "stroke_volume_ml" }: Props) {
  const panelId = useId();
  const titleId = `${panelId}-title`;
  const descriptionId = `${panelId}-description`;
  const statusId = `${panelId}-status`;
  const errorId = `${panelId}-error`;
  const resultId = `${panelId}-result`;
  const [metric, setMetric] = useState(
    TARGETS.some((target) => target.value === initialMetric) ? initialMetric : DEFAULT_METRIC,
  );
  const [result, setResult] = useState<MissingPieceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestSeq = useRef(0);

  async function analyze() {
    if (!ensembleId) return;
    const seq = ++requestSeq.current;
    const requestEnsembleId = ensembleId;
    const requestMetric = metric;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await createMissingPiece({
        baseline_ensemble_id: requestEnsembleId,
        target_metric: requestMetric,
      });
      if (
        !shouldApplyMissingPieceResult(seq, requestSeq.current, {
          ensembleId: requestEnsembleId,
          metric: requestMetric,
        }, { ensembleId, metric })
      ) {
        return;
      }
      setResult(response);
    } catch (cause) {
      if (seq !== requestSeq.current) return;
      setError(cause instanceof Error ? cause.message : "Missing Piece analysis failed");
    } finally {
      if (seq === requestSeq.current) setLoading(false);
    }
  }

  function selectMetric(nextMetric: string) {
    setMetric(nextMetric);
    setResult(null);
    setError(null);
  }

  const hasAnalysis = result !== null;
  const hasDrivers = (result?.dominant_uncertainty_drivers?.length ?? 0) > 0;
  const hasEvidence = (result?.evidence_ranking?.length ?? 0) > 0;
  const statusMessage = loading
    ? `Analyzing uncertainty for ${metricLabel(metric)}…`
    : error
      ? "The uncertainty analysis could not be completed."
      : hasAnalysis
        ? `Uncertainty analysis ready for ${result.target_metric.replaceAll("_", " ")}.`
        : ensembleId
          ? "Choose a modeled target, then explain its uncertainty."
          : "Run the plausible-twin ensemble before analyzing uncertainty.";

  return (
    <section
      className="rounded-xl border border-cyan-300/20 bg-slate-950/70 p-4 text-white"
      aria-labelledby={titleId}
      aria-busy={loading}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[.2em] text-cyan-200">M8 · research lens</p>
          <h2 id={titleId} className="mt-1 text-lg font-semibold">WHY IS THIS UNCERTAIN?</h2>
          <p id={descriptionId} className="mt-1 max-w-xl text-xs text-white/60">
            A deterministic local-sensitivity view of which modeled inputs move the selected target.
            This is an uncertainty-impact heuristic, not a probability or information-gain estimate.
          </p>
        </div>
        <label htmlFor={`${panelId}-target`} className="text-xs text-white/70">
          Target
          <select
            id={`${panelId}-target`}
            value={metric}
            onChange={(event) => selectMetric(event.target.value)}
            className="ml-2 rounded border border-white/20 bg-slate-900 px-2 py-1 text-white focus:outline-none focus:ring-2 focus:ring-cyan-300"
            aria-describedby={descriptionId}
            aria-controls={resultId}
            disabled={loading}
          >
            {TARGETS.map((target) => <option key={target.value} value={target.value}>{target.label}</option>)}
          </select>
        </label>
      </div>
      <button
        type="button"
        onClick={analyze}
        disabled={!ensembleId || loading}
        className="mt-4 rounded bg-cyan-300 px-3 py-2 text-xs font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
        aria-describedby={statusId}
        aria-busy={loading}
      >
        {loading ? "Analyzing…" : hasAnalysis ? "Re-analyze target" : "Explain uncertainty"}
      </button>

      <p id={statusId} role={error ? "alert" : "status"} aria-live={error ? "assertive" : "polite"} className="mt-3 text-xs text-white/60">
        {statusMessage}
      </p>

      {!ensembleId && (
        <div className="mt-3 rounded border border-amber-200/20 bg-amber-200/[.06] p-3 text-xs text-amber-100">
          <p className="font-medium">No plausible-twin ensemble is selected.</p>
          <p className="mt-1 text-amber-100/70">Run the ensemble first so this view can compare deterministic perturbations against its persisted baseline.</p>
        </div>
      )}

      {error && (
        <div id={errorId} className="mt-3 rounded border border-rose-200/20 bg-rose-200/[.06] p-3 text-xs text-rose-100" role="alert">
          <p className="font-medium">Analysis unavailable.</p>
          <p className="mt-1 text-rose-100/75">{error}</p>
          <button type="button" onClick={analyze} disabled={!ensembleId || loading} className="mt-2 rounded border border-rose-100/30 px-2 py-1 font-medium text-rose-50 hover:bg-rose-100/10 disabled:cursor-not-allowed disabled:opacity-50">
            Try again
          </button>
        </div>
      )}

      {!loading && !error && !hasAnalysis && ensembleId && (
        <div className="mt-4 rounded border border-white/10 bg-white/[.03] p-3 text-xs text-white/65">
          <p className="font-medium text-white">No analysis yet.</p>
          <p className="mt-1">Select a target and choose “Explain uncertainty” to inspect model sensitivity and evidence priorities.</p>
        </div>
      )}

      {result && (
        <div id={resultId} className="mt-5 space-y-5" aria-live="polite">
          <div className="rounded-lg border border-cyan-300/20 bg-cyan-300/[.04] p-3">
            <h3 className="text-sm font-medium">WHAT IS UNCERTAIN?</h3>
            <p className="mt-1 text-xs text-white/60">
              Target: <span className="font-medium text-white">{metricLabel(result.target_metric)}</span>. The values below describe bounded local model responses, not clinical measurements or probabilities.
            </p>
          </div>
          <div>
            <h3 className="text-sm font-medium">Dominant uncertainty drivers</h3>
            {hasDrivers ? (
              <ul className="mt-2 grid gap-2 sm:grid-cols-2" aria-label="Uncertainty drivers">
                {result.dominant_uncertainty_drivers.map((driver) => (
                  <li key={`${driver.parameter_id}:${driver.metric_id}`} className="rounded border border-white/10 p-2 text-xs">
                    <span className="font-medium">{driver.parameter_id}</span>
                    <span className="ml-2 text-white/60">uncertainty-impact heuristic {formatScore(driver.impact_score)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 rounded border border-white/10 p-3 text-xs text-white/60">No ranked uncertainty driver is available for this target.</p>
            )}
          </div>
          <div>
            <h3 className="mb-2 text-sm font-medium">Local sensitivity</h3>
            {result.sensitivities.length > 0 ? <SensitivityTable rows={result.sensitivities} /> : <p className="rounded border border-white/10 p-3 text-xs text-white/60" role="status">Sensitivity is unavailable for this target.</p>}
          </div>
          <div>
            <h3 className="mb-1 text-sm font-medium">WHAT WOULD HELP?</h3>
            <p className="mb-2 text-xs text-white/60">Evidence is ranked by its mapped ability to constrain influential parameters. It is a deterministic priority heuristic, not a promise of benefit or an information-gain estimate.</p>
            {hasEvidence ? <EvidenceMap ranking={result.evidence_ranking} constraints={result.evidence_constraints} /> : <p className="rounded border border-white/10 p-3 text-xs text-white/60">No evidence priority is available for this target.</p>}
          </div>
          <div className="rounded border border-white/10 p-3 text-xs text-white/60">
            <h3 className="font-medium text-white/80">Analysis coverage</h3>
            <p className="mt-1">{result.completeness.covered_parameter_count} of {result.completeness.parameter_count} modeled parameters covered ({formatScore(result.completeness.coverage_fraction)}).</p>
            {!result.completeness.complete && <p className="mt-1 text-amber-100">This analysis is incomplete; uncovered parameters remain.</p>}
          </div>
          <div className="space-y-1 border-t border-white/10 pt-3 text-[11px] text-white/50">
            <p><span className="font-medium text-white/65">Safety note:</span> This research view describes deterministic model behavior only; it is not a clinical assessment.</p>
            {result.limitations.length > 0 && <p>{result.limitations.join(" ")}</p>}
            <p className="font-medium text-white/65">Safety disclaimer: {result.safety_disclaimer}</p>
          </div>
        </div>
      )}
    </section>
  );
}
