"use client";

import { useCallback, useEffect, useState } from "react";
import { DISCLAIMER_ACK_EVENT } from "@/components/safety/DisclaimerModal";

const TOUR_KEY = "beatit:product-tour:v1";
const DISCLAIMER_KEY = "hearttwin:disclaimer-ack:v1";

const STEPS = [
  {
    target: "header",
    eyebrow: "Orientation",
    title: "Follow the live run",
    body: "The header reports the current pipeline state. If a stage fails, BeatIT shows the real error instead of substituting demo output.",
  },
  {
    target: "evidence",
    eyebrow: "1 · Evidence",
    title: "Start with what is actually known",
    body: "Load a labeled case, upload supported evidence, or enter vitals. Missing ECG, echo, imaging, or clinical context remains explicitly missing.",
  },
  {
    target: "twin",
    eyebrow: "2 · Twin and Experiment",
    title: "Inspect, then change one bounded input",
    body: "The center workspace renders the deterministic state. Use Experiment to fork an observed snapshot without rewriting its history.",
  },
  {
    target: "trace",
    eyebrow: "3 · Trust",
    title: "Watch every stage and its evaluation",
    body: "Trace, provenance, uncertainty, and failed checks stay visible. Tools establish numerical facts; optional language models only explain them.",
  },
  {
    target: "navigation",
    eyebrow: "4 · Compare and Report",
    title: "Complete the evidence-to-report journey",
    body: "Move through Twin, Experiment, Compare, Evidence, and Report. Use Split Heart and Missing Piece to explain deltas and uncertainty.",
  },
] as const;

function stored(key: string): boolean {
  try {
    return localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

export function ProductTour() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const finish = useCallback(() => {
    try {
      localStorage.setItem(TOUR_KEY, "1");
    } catch {
      /* The tour may reappear in a later private session. */
    }
    setOpen(false);
  }, []);

  useEffect(() => {
    const maybeOpen = () => {
      if (stored(DISCLAIMER_KEY) && !stored(TOUR_KEY)) setOpen(true);
    };
    maybeOpen();
    window.addEventListener(DISCLAIMER_ACK_EVENT, maybeOpen);
    return () => window.removeEventListener(DISCLAIMER_ACK_EVENT, maybeOpen);
  }, []);

  useEffect(() => {
    if (!open) return;
    const target = document.querySelector<HTMLElement>(
      `[data-tour="${STEPS[step].target}"]`,
    );
    if (!target) return;
    const previousOutline = target.style.outline;
    const previousOffset = target.style.outlineOffset;
    target.style.outline = "3px solid var(--ht-accent)";
    target.style.outlineOffset = "-3px";
    target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return () => {
      target.style.outline = previousOutline;
      target.style.outlineOffset = previousOffset;
    };
  }, [open, step]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") finish();
      if (event.key === "ArrowRight") setStep((value) => Math.min(value + 1, STEPS.length - 1));
      if (event.key === "ArrowLeft") setStep((value) => Math.max(value - 1, 0));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [finish, open]);

  if (!open) return null;
  const current = STEPS[step];

  return (
    <aside
      role="dialog"
      aria-modal="false"
      aria-labelledby="beatit-tour-title"
      className="fixed bottom-5 right-5 z-[110] w-[min(24rem,calc(100vw-2rem))] rounded-[var(--ht-r-lg)] border border-[var(--ht-line)] bg-[var(--ht-surface-1)] p-5 shadow-2xl"
    >
      <div className="flex items-center justify-between gap-4">
        <span className="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-accent">
          {current.eyebrow}
        </span>
        <button
          type="button"
          onClick={finish}
          className="text-xs text-muted underline-offset-4 hover:text-ink hover:underline"
          aria-label="Skip product tour"
        >
          Skip
        </button>
      </div>
      <h2 id="beatit-tour-title" className="mt-2 text-lg font-semibold text-ink">
        {current.title}
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-ink-2">{current.body}</p>

      <div className="mt-4 flex gap-1.5" aria-label={`Step ${step + 1} of ${STEPS.length}`}>
        {STEPS.map((item, index) => (
          <button
            key={item.title}
            type="button"
            onClick={() => setStep(index)}
            aria-label={`Go to step ${index + 1}`}
            aria-current={index === step ? "step" : undefined}
            className={`h-1.5 flex-1 rounded-full ${
              index === step ? "bg-[var(--ht-accent)]" : "bg-[var(--ht-line)]"
            }`}
          />
        ))}
      </div>

      <div className="mt-5 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => setStep((value) => Math.max(value - 1, 0))}
          disabled={step === 0}
          className="rounded-[var(--ht-r-sm)] border border-[var(--ht-line)] px-3 py-2 text-sm text-ink disabled:cursor-not-allowed disabled:opacity-40"
        >
          Back
        </button>
        <span className="text-xs tabular-nums text-muted">
          {step + 1} / {STEPS.length}
        </span>
        <button
          type="button"
          onClick={() => {
            if (step === STEPS.length - 1) finish();
            else setStep((value) => value + 1);
          }}
          className="rounded-[var(--ht-r-sm)] bg-[var(--ht-accent)] px-4 py-2 text-sm font-medium text-[var(--ht-accent-ink)]"
        >
          {step === STEPS.length - 1 ? "Enter BeatIT" : "Next"}
        </button>
      </div>
      <p className="mt-3 text-center text-[0.68rem] text-muted">
        Use ← → to navigate · Esc to dismiss
      </p>
    </aside>
  );
}
