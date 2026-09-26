import { useId } from "react";
import type { ReactNode } from "react";

/**
 * Narrow local view of the comparison model needed by this table.
 *
 * The comparison layer supplies these values. This component deliberately
 * does not derive cardiac metrics, deltas, or direction categories.
 */
export interface ComparisonMetric {
  readonly id: string;
  readonly label: string;
  readonly baseline: number | null;
  readonly scenario: number | null;
  readonly delta: number | null;
  readonly valueUnit: string;
  readonly deltaUnit: string;
  readonly direction: "increase" | "decrease" | "neutral" | "unavailable";
  readonly changed: boolean;
}

export interface ComparisonMetricsModel {
  readonly baselineLabel: string;
  readonly scenarioLabel: string;
  readonly metrics: readonly ComparisonMetric[];
}

export interface ComparisonMetricsProps {
  readonly model: ComparisonMetricsModel | null;
  readonly differenceOnly?: boolean;
  readonly description?: ReactNode;
}

function deltaUnitFor(metric: ComparisonMetric): string {
  if (metric.id === "ejection_fraction_pct" || metric.deltaUnit === "percentage_points") {
    return "percentage points";
  }
  return metric.deltaUnit;
}

function decimalsFor(unit: string): number {
  if (unit === "L/min") return 2;
  if (unit === "bpm") return 0;
  return 1;
}

function formatValue(value: number | null, unit: string): string {
  if (value === null || !Number.isFinite(value)) return "Unavailable";
  return `${value.toFixed(decimalsFor(unit))} ${unit}`;
}

function formatDelta(value: number | null, unit: string): string {
  if (value === null || !Number.isFinite(value)) return "Unavailable";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimalsFor(unit))} ${unit}`;
}

function directionLabel(direction: ComparisonMetric["direction"]): string {
  switch (direction) {
    case "increase":
      return "Increase";
    case "decrease":
      return "Decrease";
    case "neutral":
      return "Neutral";
    default:
      return "Unavailable";
  }
}

export function ComparisonMetrics({
  model,
  differenceOnly = false,
  description = "Reported values and deltas from the paired comparison model; no physiology is recomputed here.",
}: ComparisonMetricsProps) {
  const instanceId = useId();
  const titleId = `${instanceId}-title`;
  const descriptionId = `${instanceId}-description`;
  const visibleMetrics = model
    ? differenceOnly
      ? model.metrics.filter((metric) => metric.changed)
      : model.metrics
    : [];

  return (
    <section
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      className="ht-panel overflow-hidden"
    >
      <header className="border-b border-[var(--ht-line)] px-4 py-3">
        <h2 id={titleId} className="text-[0.78rem] font-semibold uppercase tracking-[0.14em] text-ink">
          Central metrics
        </h2>
        {description ? (
          <p id={descriptionId} className="mt-1 text-xs leading-relaxed text-muted">
            {description}
          </p>
        ) : null}
      </header>

      {!model ? (
        <p className="px-4 py-4 text-xs text-muted">No comparison metrics are available.</p>
      ) : model.metrics.length === 0 ? (
        <p className="px-4 py-4 text-xs text-muted">No metrics were returned by the comparison model.</p>
      ) : visibleMetrics.length === 0 ? (
        <p className="px-4 py-4 text-xs text-muted">No changed metrics were returned by the comparison model.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] border-collapse text-left text-xs">
            <caption className="sr-only">
              Comparison of central metrics between {model.baselineLabel} and {model.scenarioLabel}
            </caption>
            <thead>
              <tr className="border-b border-[var(--ht-line)] text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-muted">
                <th scope="col" className="px-3 py-2 font-semibold">Metric</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">{model.baselineLabel}</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">{model.scenarioLabel}</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Delta</th>
                <th scope="col" className="px-3 py-2 font-semibold">Direction</th>
              </tr>
            </thead>
            <tbody>
              {visibleMetrics.map((metric) => {
                const valueUnit = metric.id === "ejection_fraction_pct" ? "%" : metric.valueUnit;
                const deltaUnit = deltaUnitFor(metric);
                const direction = directionLabel(metric.direction);
                return (
                  <tr key={metric.id} className="border-b border-[var(--ht-line)] last:border-b-0">
                    <th scope="row" className="px-3 py-2.5 font-medium text-ink-2">
                      {metric.label}
                      <span className="ml-1 whitespace-nowrap text-muted">({valueUnit})</span>
                    </th>
                    <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono tabular-nums text-muted">
                      {formatValue(metric.baseline, valueUnit)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono tabular-nums text-ink-2">
                      {formatValue(metric.scenario, valueUnit)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono tabular-nums text-ink-2">
                      {formatDelta(metric.delta, deltaUnit)}
                    </td>
                    <td className="px-3 py-2.5 text-muted">
                      <span aria-label={`${metric.label} direction: ${direction}`}>{direction}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default ComparisonMetrics;
