export const SOURCE_STATUSES = ["observed", "derived", "simulated", "prior", "synthetic"] as const;
export type SourceStatus = (typeof SOURCE_STATUSES)[number];

export const SOURCE_STATUS_LABELS: Record<SourceStatus, string> = {
  observed: "OBSERVED",
  derived: "DERIVED",
  simulated: "SIMULATED",
  prior: "PRIOR",
  synthetic: "SYNTHETIC",
};

export function sourceStatusLabel(status: SourceStatus): string {
  return SOURCE_STATUS_LABELS[status];
}
