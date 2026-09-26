"use client";

import { sourceStatusLabel, type SourceStatus } from "@/lib/product/sourceStatus";

export function SourceStatusBadge({ status }: { status: SourceStatus }) {
  const warning = status === "simulated" || status === "synthetic";
  const label = sourceStatusLabel(status);
  return <span className="ht-chip" data-status={warning ? "warning" : status === "observed" ? "success" : "running"} aria-label={`Source status: ${label}`}>{label}</span>;
}
