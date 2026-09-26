import type { TwinEnsemble } from "@/lib/twin/ensemble/contracts";
import { getComponentUncertaintyView, metricLabel } from "@/lib/twin/ensemble/inspectorModel";

function format(value: number, unit: string): string {
  return `${value.toFixed(unit === "%" ? 1 : 2)} ${unit}`;
}

export function EnsembleUncertaintyInspector({
  ensemble,
  componentId = "left-ventricle",
}: {
  ensemble: TwinEnsemble;
  componentId?: string;
}) {
  const view = getComponentUncertaintyView(ensemble, componentId);
  return (
    <section className="mt-2 border border-[var(--ht-line)] bg-[var(--ht-surface-2)] p-2" aria-label={`${view.componentLabel} uncertainty inspector`}>
      <h3 className="text-[0.62rem] font-semibold tracking-[0.08em] text-ink">{view.componentLabel.toUpperCase()} UNCERTAINTY</h3>
      {view.distributions.length > 0 ? (
        <ul className="mt-1 space-y-1">
          {view.distributions.map((distribution) => (
            <li key={distribution.metricId} className="flex min-w-0 flex-wrap items-baseline justify-between gap-2 text-[0.6rem] text-muted">
              <span className="min-w-0 break-words">{metricLabel(distribution.metricId)}</span>
              <span className="ht-mono">5th–95th percentile: {format(distribution.quantiles.q05, distribution.unit)}–{format(distribution.quantiles.q95, distribution.unit)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-[0.6rem] text-muted">{view.unavailableMessage}</p>
      )}
      <p className="mt-1 text-[0.58rem] text-muted">Origin quality: {view.originQualityLabel} · seed {ensemble.seed} · {ensemble.acceptedSampleCount} accepted samples.</p>
      <p className="mt-1 text-[0.58rem] text-muted">Lineage source: {view.provenanceSourceLabel}.</p>
      <p className="mt-1 text-[0.58rem] text-muted">Mapped scalar outputs only; not a geometric or clinical confidence estimate.</p>
    </section>
  );
}
