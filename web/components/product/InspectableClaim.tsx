"use client";

import { useState } from "react";
import { ProvenanceInspectPanel, type ProvenanceInspectPayload } from "./ProvenanceInspectPanel";

type Props = {
  label: string;
  value: string;
  provenance: ProvenanceInspectPayload;
  className?: string;
};

export function InspectableClaim({ label, value, provenance, className }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        className={className ?? "group inline-flex flex-col items-start rounded border border-transparent px-1 py-0.5 text-left hover:border-[var(--ht-line)] hover:bg-[var(--ht-surface-2)] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"}
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <span className="text-[0.62rem] uppercase tracking-[0.08em] text-muted">{label}</span>
        <span className="text-sm font-semibold tabular-nums text-ink group-hover:underline">{value}</span>
        <span className="sr-only">Inspect source for {label}</span>
      </button>
      <ProvenanceInspectPanel open={open} payload={provenance} onClose={() => setOpen(false)} />
    </>
  );
}
