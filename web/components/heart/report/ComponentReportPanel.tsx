"use client";

import { X } from "@phosphor-icons/react";
import type { ComponentReport } from "@/lib/heart/contracts";

export function ComponentReportPanel({ report, onClose }: { report: ComponentReport; onClose: () => void }) {
  return <div role="dialog" aria-modal="true" aria-label={`${report.component.displayName} report`} className="absolute inset-0 z-30 overflow-y-auto bg-[var(--ht-surface-1)] p-5">
    <div className="mx-auto max-w-2xl"><div className="flex items-start justify-between"><div><p className="ht-eyebrow">BeatIT component report</p><h2 className="mt-1 text-xl font-semibold">{report.component.displayName}</h2></div><button type="button" aria-label="Close report" onClick={onClose} className="ht-btn ht-btn-ghost"><X size={16} /></button></div>
      <div className="mt-5 space-y-5">{report.sections.map((section) => <section key={section.id}><h3 className="ht-eyebrow">{section.title}</h3><div className="mt-2 space-y-1 text-sm text-ink-2">{section.lines.map((line) => <p key={line}>{line}</p>)}</div></section>)}</div>
      <p className="mt-8 border-t border-[var(--ht-line)] pt-3 text-xs text-muted">{report.safetyNotice}</p>
    </div>
  </div>;
}
