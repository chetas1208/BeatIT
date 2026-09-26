"use client";

/*
 * Local trace linkage — opens the case trace JSON API (no W&B Weave).
 * READS from store: weave (WeaveInfo-shaped payload from backend).
 */

import { ArrowSquareOut, Graph } from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { useDualBeatStore } from "@/lib/store";

export function WeaveBadge() {
  const weave = useDualBeatStore((s) => s.weave);
  const reduce = useReducedMotion() ?? false;

  const status = weave?.status ?? "local";
  const local = status === "local" || status === "connected";
  const url = weave?.run_url ?? weave?.project_url ?? null;
  const stages = weave?.traced_stages_count;
  const tools = weave?.traced_tool_calls_count;
  const hasCounts = typeof stages === "number" || typeof tools === "number";

  if (!local || !url) {
    return (
      <span className="ht-chip" data-status="idle" title="Local agent traces">
        <Graph weight="duotone" className="size-3.5" />
        Traces standby
      </span>
    );
  }

  return (
    <motion.a
      href={url}
      target="_blank"
      rel="noreferrer noopener"
      title="Open local pipeline trace (JSON API)"
      initial={reduce ? false : { opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      whileHover={reduce ? undefined : { y: -1 }}
      whileTap={reduce ? undefined : { scale: 0.98 }}
      className="group inline-flex items-center gap-2 rounded-[var(--ht-r-md)] border border-[var(--ht-signal-line)] bg-[var(--ht-signal-soft)] px-2.5 py-1.5 text-signal-bright transition-colors hover:bg-[color-mix(in_oklab,var(--ht-signal-soft)_60%,var(--ht-surface-3))]"
    >
      <span className="ht-pulse relative grid place-items-center text-ecg">
        <span className="ht-chip-dot" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="text-[0.78rem] font-semibold">View local trace</span>
        <span className="ht-mono text-[0.62rem] text-signal-dim">
          {weave?.project ?? "local-traces"}
          {hasCounts ? (
            <>
              {" · "}
              {typeof stages === "number" ? `${stages} stages` : null}
              {typeof stages === "number" && typeof tools === "number" ? " · " : null}
              {typeof tools === "number" ? `${tools} tools` : null}
            </>
          ) : null}
        </span>
      </span>
      <ArrowSquareOut
        weight="bold"
        className="size-3.5 opacity-70 transition-opacity group-hover:opacity-100"
      />
    </motion.a>
  );
}
