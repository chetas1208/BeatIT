"use client";

import { ArrowLeft, X } from "@phosphor-icons/react";
import { useEffect, useRef } from "react";
import { PRODUCT_SPACES, type BeatITMode } from "@/lib/product/contracts";

interface ProductNavigationProps {
  mode: BeatITMode;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  onSelect: (mode: BeatITMode) => void;
}

export function ProductNavigation({ mode, open, onOpen, onClose, onSelect }: ProductNavigationProps) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) {
      triggerRef.current?.focus();
      return;
    }
    closeRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const dialog = document.getElementById("beatit-space-drawer");
      if (!dialog) return;
      const focusable = Array.from(dialog.querySelectorAll<HTMLElement>("button, [href], select, textarea, input, [tabindex]:not([tabindex='-1'])"));
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <>
      <nav aria-label="BeatIT primary spaces" className="flex min-w-0 items-center gap-1 overflow-x-auto border-b border-[var(--ht-line)] bg-[var(--ht-surface-1)] px-2 py-1.5">
        <button ref={triggerRef} type="button" className="ht-btn ht-btn-secondary mr-1 min-h-8 shrink-0 px-2 text-xs" onClick={onOpen} aria-expanded={open} aria-controls="beatit-space-drawer">
          <span aria-hidden="true">☰</span><span className="sr-only">Open product spaces</span>
        </button>
        {PRODUCT_SPACES.map((space) => (
          <button key={space.id} type="button" className={`min-h-8 shrink-0 border-b-2 px-2.5 text-[0.68rem] font-semibold tracking-[0.1em] transition-colors ${mode === space.id ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"}`} onClick={() => onSelect(space.id)} aria-current={mode === space.id ? "page" : undefined}>
            {space.shortLabel}
          </button>
        ))}
      </nav>
      {open ? (
        <div className="fixed inset-0 z-[var(--ht-z-backdrop)]" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
          <div id="beatit-space-drawer" role="dialog" aria-modal="true" aria-labelledby="beatit-space-title" className="h-full w-[min(22rem,88vw)] border-r-2 border-[var(--ht-line-strong)] bg-[var(--ht-surface-1)] p-4 shadow-xl">
            <div className="flex items-center justify-between gap-3">
              <div><p className="ht-eyebrow">BeatIT product</p><h2 id="beatit-space-title" className="mt-1 text-lg font-semibold text-ink">Choose a space</h2></div>
              <button ref={closeRef} type="button" className="ht-btn ht-btn-ghost min-h-8 px-2" onClick={onClose} aria-label="Close product spaces"><X className="size-4" /></button>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted">The heart and active case stay in context while you move through one computational story.</p>
            <div className="mt-4 space-y-1">
              {PRODUCT_SPACES.map((space) => (
                <button key={space.id} type="button" className={`flex w-full items-start gap-3 border px-3 py-3 text-left ${mode === space.id ? "border-accent bg-accent/10" : "border-[var(--ht-line)] hover:bg-[var(--ht-surface-2)]"}`} onClick={() => onSelect(space.id)}>
                  <span className="mt-0.5 text-[0.62rem] font-bold tracking-[0.12em] text-signal">{space.shortLabel}</span>
                  <span><span className="block text-sm font-semibold text-ink">{space.label}</span><span className="mt-0.5 block text-xs text-muted">{space.description}</span></span>
                </button>
              ))}
            </div>
            <button type="button" className="ht-btn ht-btn-ghost mt-5 min-h-8 px-2 text-xs" onClick={onClose}><ArrowLeft className="size-3.5" /> Return to workspace</button>
          </div>
        </div>
      ) : null}
    </>
  );
}
