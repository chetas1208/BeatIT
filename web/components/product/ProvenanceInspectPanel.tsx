"use client";

import { X } from "@phosphor-icons/react";
import { useEffect, useId, useRef } from "react";

export type ProvenanceInspectPayload = {
  title: string;
  sourceLabel: string;
  sourceType: string;
  capturedAt?: string | null;
  derivation?: string | null;
  usedBy?: readonly string[];
  method?: string | null;
};

type Props = {
  open: boolean;
  payload: ProvenanceInspectPayload | null;
  onClose: () => void;
};

export function ProvenanceInspectPanel({ open, payload, onClose }: Props) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open || !payload) return null;

  return (
    <div className="fixed inset-0 z-[var(--ht-z-modal)] flex items-end justify-center p-4 sm:items-center" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section role="dialog" aria-modal="true" aria-labelledby={titleId} className="w-full max-w-md border-2 border-[var(--ht-line-strong)] bg-[var(--ht-surface-1)] p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="ht-eyebrow">Inspect source</p>
            <h2 id={titleId} className="mt-1 text-base font-semibold text-ink">{payload.title}</h2>
          </div>
          <button ref={closeRef} type="button" className="ht-btn ht-btn-ghost min-h-8 px-2" onClick={onClose} aria-label="Close source inspection">
            <X className="size-4" />
          </button>
        </div>
        <dl className="mt-4 space-y-3 text-xs">
          <div>
            <dt className="font-semibold uppercase tracking-[0.08em] text-muted">Source</dt>
            <dd className="mt-0.5 text-ink">{payload.sourceLabel}</dd>
            {payload.capturedAt ? <dd className="mt-0.5 text-muted">{payload.capturedAt}</dd> : null}
          </div>
          <div>
            <dt className="font-semibold uppercase tracking-[0.08em] text-muted">Type</dt>
            <dd className="mt-0.5 text-ink">{payload.sourceType}</dd>
          </div>
          {payload.method ? (
            <div>
              <dt className="font-semibold uppercase tracking-[0.08em] text-muted">Method</dt>
              <dd className="mt-0.5 text-ink">{payload.method}</dd>
            </div>
          ) : null}
          {payload.derivation ? (
            <div>
              <dt className="font-semibold uppercase tracking-[0.08em] text-muted">Derivation</dt>
              <dd className="mt-0.5 leading-relaxed text-ink-2">{payload.derivation}</dd>
            </div>
          ) : null}
          {payload.usedBy && payload.usedBy.length > 0 ? (
            <div>
              <dt className="font-semibold uppercase tracking-[0.08em] text-muted">Used by</dt>
              <dd className="mt-0.5 text-ink">{payload.usedBy.join(" · ")}</dd>
            </div>
          ) : null}
        </dl>
        <p className="mt-4 border-t border-[var(--ht-line)] pt-3 text-[0.65rem] leading-relaxed text-muted">
          Provenance describes how this value entered the twin. It is not a clinical recommendation or verification of patient truth.
        </p>
      </section>
    </div>
  );
}
