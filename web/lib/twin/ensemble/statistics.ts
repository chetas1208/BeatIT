import type { OutputDistribution } from "@/lib/twin/ensemble/contracts";

function assertSamples(values: readonly number[]): number[] {
  if (values.length === 0 || values.some((value) => !Number.isFinite(value))) throw new RangeError("Statistics require finite samples");
  return [...values].sort((a, b) => a - b);
}

function quantile(sorted: readonly number[], probability: number): number {
  const position = (sorted.length - 1) * probability;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower]!;
  return sorted[lower]! + (sorted[upper]! - sorted[lower]!) * (position - lower);
}

export function summarizeDistribution(metricId: string, unit: string, values: readonly number[]): OutputDistribution {
  const sorted = assertSamples(values);
  const mean = sorted.reduce((total, value) => total + value, 0) / sorted.length;
  const variance = sorted.reduce((total, value) => total + (value - mean) ** 2, 0) / sorted.length;
  return {
    metricId,
    unit,
    samples: sorted,
    mean,
    median: quantile(sorted, 0.5),
    variance,
    standardDeviation: Math.sqrt(variance),
    quantiles: { q05: quantile(sorted, 0.05), q25: quantile(sorted, 0.25), q75: quantile(sorted, 0.75), q95: quantile(sorted, 0.95) },
    min: sorted[0]!,
    max: sorted[sorted.length - 1]!,
  };
}

export function metricValue(state: { measurements: object }, metricId: string): number | null {
  const measurements = state.measurements as Record<string, { value?: number } | null | undefined>;
  const value = measurements[metricId]?.value;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
