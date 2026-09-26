import { componentViews } from "@/lib/twin/scenario/components";
import type { ComponentDelta, ScenarioResult } from "@/lib/twin/scenario/types";

export interface ScenarioInspectorProps {
  result: ScenarioResult | null;
}

type ProvenanceEntry = ScenarioResult["provenance"][number];

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "Unavailable";
  const normalized = Math.abs(value) < 0.005 ? 0 : value;
  return normalized.toFixed(2);
}

function formatDelta(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "Unavailable";
  return `${value > 0 ? "+" : ""}${formatNumber(value)}`;
}

function formatTimestamp(value: string): string {
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.getTime()) ? value : timestamp.toISOString();
}

function provenanceLabel(entry: ProvenanceEntry): string {
  return [humanize(entry.source), entry.method].filter(Boolean).join(" · ");
}

function ProvenanceDetails({
  provenance,
  label = "Metric provenance",
}: {
  provenance: readonly ProvenanceEntry[];
  label?: string;
}) {
  if (provenance.length === 0) {
    return <span className="text-muted">No provenance recorded</span>;
  }

  return (
    <details className="group">
      <summary className="cursor-pointer list-none text-xs text-signal-bright group-open:mb-2 [&::-webkit-details-marker]:hidden">
        {label} · {provenance.length}
      </summary>
      <ul className="space-y-2 text-[0.68rem] leading-relaxed text-muted">
        {provenance.map((entry, index) => (
          <li key={`${entry.source}-${entry.method ?? "source"}-${index}`}>
            <div className="font-medium text-ink-2">{provenanceLabel(entry)}</div>
            {entry.sourceId ? <div>Source ID: {entry.sourceId}</div> : null}
            {entry.confidence === undefined ? null : (
              <div>Confidence: {Math.round(entry.confidence * 100)}%</div>
            )}
            {entry.evidenceIds?.length ? (
              <div>Evidence: {entry.evidenceIds.join(", ")}</div>
            ) : null}
            {entry.note ? <div>{entry.note}</div> : null}
          </li>
        ))}
      </ul>
    </details>
  );
}

function DeltaTable({ deltas }: { deltas: readonly ComponentDelta[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[42rem] border-collapse text-left text-xs">
        <caption className="sr-only">Baseline and scenario component values</caption>
        <thead>
          <tr className="border-b border-[var(--ht-line)] text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-muted">
            <th scope="col" className="px-2 py-2 font-semibold">Metric</th>
            <th scope="col" className="px-2 py-2 text-right font-semibold">Baseline</th>
            <th scope="col" className="px-2 py-2 text-right font-semibold">Scenario</th>
            <th scope="col" className="px-2 py-2 text-right font-semibold">Delta</th>
            <th scope="col" className="px-2 py-2 font-semibold">Provenance</th>
          </tr>
        </thead>
        <tbody>
          {deltas.map((delta) => (
            <tr key={`${delta.componentId}-${delta.metric}`} className="border-b border-[var(--ht-line)] last:border-b-0">
              <th scope="row" className="px-2 py-2.5 font-medium text-ink-2">
                {humanize(delta.metric)}
                {delta.unit ? <span className="ml-1 text-muted">({delta.unit})</span> : null}
              </th>
              <td className="px-2 py-2.5 text-right font-mono text-muted">{formatNumber(delta.baseline)}</td>
              <td className="px-2 py-2.5 text-right font-mono text-ink-2">{formatNumber(delta.scenario)}</td>
              <td
                className={`px-2 py-2.5 text-right font-mono ${
                  delta.direction === "increase"
                    ? "text-ecg"
                    : delta.direction === "decrease"
                      ? "text-accent-bright"
                      : "text-muted"
                }`}
              >
                {formatDelta(delta.delta)}
              </td>
              <td className="max-w-[15rem] px-2 py-2.5 align-top">
                <ProvenanceDetails provenance={delta.provenance} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SafetyBoundary({ result }: { result: ScenarioResult }) {
  return (
    <section
      aria-labelledby="scenario-inspector-safety"
      className="border border-[var(--ht-warn-line)] bg-[var(--ht-warn-soft)] p-3"
    >
      <h3 id="scenario-inspector-safety" className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-warn">
        Safety boundary
      </h3>
      <p className="mt-2 text-sm font-medium text-ink-2">Hypothetical scenario only</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">
        {result.definition.description ?? "This is a bounded counterfactual comparison."} It is not a diagnosis, treatment recommendation, or clinical prediction.
      </p>
      {result.warnings.length ? (
        <ul className="mt-2 space-y-1 text-xs leading-relaxed text-muted">
          {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
        </ul>
      ) : null}
    </section>
  );
}

export function ScenarioInspector({ result }: ScenarioInspectorProps) {
  if (!result) {
    return (
      <section aria-label="Scenario inspector" className="ht-panel p-4">
        <p className="ht-eyebrow">Scenario inspector</p>
        <p className="mt-2 text-sm text-muted">Run a scenario to inspect baseline and scenario component values.</p>
      </section>
    );
  }

  const views = componentViews(result.componentDeltas);

  return (
    <section aria-labelledby="scenario-inspector-title" className="ht-panel overflow-hidden">
      <header className="border-b border-[var(--ht-line)] px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="ht-eyebrow">Scenario inspector</p>
            <h2 id="scenario-inspector-title" className="mt-1 text-lg font-semibold text-ink">
              {result.definition.label}
            </h2>
            <p className="mt-1 text-xs text-muted">
              {humanize(result.status)} · computed {formatTimestamp(result.computedAt)}
            </p>
          </div>
          <span className="ht-chip" data-status="warning">Hypothetical</span>
        </div>
        <dl className="mt-3 grid gap-2 border-t border-[var(--ht-line)] pt-3 text-xs sm:grid-cols-2">
          <div>
            <dt className="text-muted">Baseline snapshot</dt>
            <dd className="mt-0.5 font-mono text-ink-2">{result.baseline.snapshotId}</dd>
          </div>
          <div>
            <dt className="text-muted">Scenario ID</dt>
            <dd className="mt-0.5 font-mono text-ink-2">{result.scenario.scenarioId}</dd>
          </div>
        </dl>
      </header>

      <div className="space-y-4 p-4">
        <SafetyBoundary result={result} />

        <section aria-labelledby="scenario-inspector-deltas">
          <div className="flex items-baseline justify-between gap-3">
            <div>
              <h3 id="scenario-inspector-deltas" className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-signal-bright">
                Component deltas
              </h3>
              <p className="mt-1 text-xs text-muted">Observed baseline compared with the computed scenario state.</p>
            </div>
            <span className="text-xs text-muted">{result.componentDeltas.length} metric{result.componentDeltas.length === 1 ? "" : "s"}</span>
          </div>

          {views.length ? (
            <div className="mt-3 space-y-3">
              {views.map((view) => (
                <section key={view.componentId} aria-labelledby={`scenario-component-${view.componentId}`} className="border border-[var(--ht-line)] bg-surface-2/40">
                  <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[var(--ht-line)] px-3 py-2">
                    <h4 id={`scenario-component-${view.componentId}`} className="font-medium text-ink-2">{view.displayName}</h4>
                    <span className="text-[0.68rem] capitalize text-muted">{humanize(view.category)}</span>
                  </header>
                  <div className="px-1 py-1"><DeltaTable deltas={view.deltas} /></div>
                </section>
              ))}
            </div>
          ) : (
            <p className="mt-3 border border-dashed border-[var(--ht-line)] p-3 text-xs text-muted">No component deltas were produced.</p>
          )}
        </section>

        <section aria-labelledby="scenario-inspector-provenance" className="border-t border-[var(--ht-line)] pt-4">
          <h3 id="scenario-inspector-provenance" className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-signal-bright">Provenance</h3>
          <p className="mt-1 text-xs leading-relaxed text-muted">
            Baseline origin: {result.baseline.patientId} · {formatTimestamp(result.baseline.timestamp)}
          </p>
          <div className="mt-2"><ProvenanceDetails provenance={result.provenance} label="Scenario provenance" /></div>
          {result.baseline.evidenceIds.length ? (
            <p className="mt-2 text-[0.68rem] text-muted">Baseline evidence: {result.baseline.evidenceIds.join(", ")}</p>
          ) : null}
        </section>
      </div>
    </section>
  );
}

export default ScenarioInspector;
