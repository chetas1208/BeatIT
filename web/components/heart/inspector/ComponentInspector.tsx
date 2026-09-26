"use client";

import { CaretDown, Info, X } from "@phosphor-icons/react";
import { useMemo } from "react";
import type {
  AnatomyKnowledge,
  ComponentReport,
  PatientBindingInput,
  PatientComponentState,
} from "@/lib/heart/contracts";
import { buildComponentInspectorModel } from "./model";

interface ComponentInspectorProps {
  report: ComponentReport;
  onClose: () => void;
  onReport: () => void;
  knowledge?: AnatomyKnowledge;
  patientState?: PatientComponentState;
}

interface InspectorContentProps {
  report: ComponentReport;
  knowledge: AnatomyKnowledge;
  patientState: PatientComponentState;
  onClose: () => void;
  onReport: () => void;
}

function formatCategory(category: ComponentReport["component"]["category"]): string {
  return category.replaceAll("_", " ");
}

function formatStatus(status: PatientComponentState["statusLabel"]): string {
  return status.replaceAll("_", " ");
}

function Disclosure({
  title,
  count,
  children,
  open = false,
}: {
  title: string;
  count?: number;
  children: React.ReactNode;
  open?: boolean;
}) {
  return (
    <details open={open} className="group border-t border-[var(--ht-line)] py-3">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted [&::-webkit-details-marker]:hidden">
        <span>{title}{count === undefined ? "" : ` · ${count}`}</span>
        <CaretDown size={14} aria-hidden="true" className="transition-transform group-open:rotate-180" />
      </summary>
      <div className="mt-2">{children}</div>
    </details>
  );
}

function Evidence({ patientState }: { patientState: PatientComponentState }) {
  if (!patientState.evidence.length) {
    return <p className="text-xs leading-relaxed text-muted">No component-specific provenance is available.</p>;
  }

  return (
    <ul className="space-y-2">
      {patientState.evidence.map((entry) => (
        <li key={entry.id} className="border-l-2 border-[var(--ht-signal)] pl-2 text-xs">
          <div className="font-medium text-ink">{entry.label}</div>
          <div className="text-muted">
            {entry.kind}
            {entry.source ? ` · ${entry.source}` : ""}
            {entry.confidence == null ? "" : ` · confidence ${Math.round(entry.confidence * 100)}%`}
          </div>
        </li>
      ))}
    </ul>
  );
}

function InspectorContent({ report, knowledge, patientState, onClose, onReport }: InspectorContentProps) {
  const metrics = patientState.metrics.slice(0, 3);
  const remainingMetricCount = patientState.metrics.length - metrics.length;

  return (
    <aside
      aria-label={`${report.component.displayName} inspector`}
      className="absolute inset-y-0 right-0 z-20 w-[min(23rem,92%)] overflow-y-auto border-l border-[var(--ht-line)] bg-[var(--ht-surface-1)]/95 p-4 shadow-xl backdrop-blur-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="ht-eyebrow">Selected anatomy</p>
          <h2 className="mt-1 text-lg font-semibold text-ink">{report.component.displayName}</h2>
          <p className="mt-1 text-xs capitalize text-muted">{formatCategory(report.component.category)}</p>
        </div>
        <button type="button" aria-label="Close component inspector" onClick={onClose} className="ht-btn ht-btn-ghost">
          <X size={16} />
        </button>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3 border-y border-[var(--ht-line)] py-2 text-xs">
        <span className="text-muted">Patient state</span>
        <span className="rounded-full border border-[var(--ht-line)] px-2 py-0.5 capitalize text-ink-2">
          {formatStatus(patientState.statusLabel)}
        </span>
      </div>

      <section className="mt-4" aria-labelledby="component-inspector-overview">
        <h3 id="component-inspector-overview" className="ht-eyebrow">Overview</h3>
        <p className="mt-2 text-sm leading-relaxed text-ink-2">{knowledge.shortDescription}</p>
        <p className="mt-2 text-xs leading-relaxed text-muted">Normal function: {knowledge.primaryFunction}</p>
      </section>

      {patientState.available ? (
        <section className="mt-4" aria-labelledby="component-inspector-state">
          <h3 id="component-inspector-state" className="ht-eyebrow">Current state</h3>
          <dl className="mt-2 space-y-1.5 text-xs">
            {metrics.map((metric) => (
              <div key={metric.label} className="flex items-baseline justify-between gap-3">
                <dt className="text-muted">{metric.label}</dt>
                <dd className="text-right text-ink-2">{metric.value}</dd>
              </div>
            ))}
          </dl>
          {remainingMetricCount > 0 ? (
            <p className="mt-2 text-[0.68rem] text-muted">{remainingMetricCount} more value{remainingMetricCount === 1 ? "" : "s"} in patient state.</p>
          ) : null}
        </section>
      ) : (
        <div className="mt-4 flex gap-2 border border-[var(--ht-line)] p-3 text-xs leading-relaxed text-muted" role="status">
          <Info size={16} aria-hidden="true" className="mt-0.5 flex-none text-[var(--ht-signal-bright)]" />
          <span>No patient-specific state is available for this component.</span>
        </div>
      )}

      <div className="mt-4">
        <Disclosure title="Findings" count={patientState.findings.length} open={patientState.findings.length > 0}>
          {patientState.findings.length ? (
            <ul className="space-y-2 text-xs leading-relaxed text-ink-2">
              {patientState.findings.map((finding) => <li key={finding.id}><span className="font-medium">{finding.title}:</span> {finding.summary}</li>)}
            </ul>
          ) : <p className="text-xs text-muted">No localized findings are linked to this component.</p>}
        </Disclosure>

        <Disclosure title="Evidence" count={patientState.evidence.length}>
          <Evidence patientState={patientState} />
        </Disclosure>

        <Disclosure title="Related structures" count={knowledge.relatedStructures.length}>
          {knowledge.relatedStructures.length ? (
            <ul className="space-y-1 text-xs text-ink-2">
              {knowledge.relatedStructures.map((structure) => <li key={structure}>{structure.replaceAll("-", " ")}</li>)}
            </ul>
          ) : <p className="text-xs text-muted">No related structures are registered.</p>}
        </Disclosure>

        {patientState.limitations.length ? (
          <Disclosure title="Limitations" count={patientState.limitations.length}>
            <ul className="space-y-1 text-xs leading-relaxed text-muted">
              {patientState.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
            </ul>
          </Disclosure>
        ) : null}
      </div>

      <p className="mt-2 border-t border-[var(--ht-line)] pt-3 text-xs leading-relaxed text-muted">{report.safetyNotice}</p>
      <button type="button" onClick={onReport} className="ht-btn ht-btn-primary mt-4 w-full">View component report</button>
    </aside>
  );
}

export function ComponentInspector({ report, onClose, onReport, knowledge, patientState }: ComponentInspectorProps) {
  return <InspectorContent report={report} knowledge={knowledge ?? report.knowledge} patientState={patientState ?? report.patientState} onClose={onClose} onReport={onReport} />;
}

export function SelectedComponentInspector({ componentId, input, onClose, onReport }: { componentId: string | null; input: PatientBindingInput; onClose: () => void; onReport: () => void }) {
  const model = useMemo(() => (componentId ? buildComponentInspectorModel(componentId, input) : null), [componentId, input]);

  if (!componentId) return null;
  if (!model) {
    return (
      <aside aria-label="Component inspector" className="absolute inset-y-0 right-0 z-20 w-[min(23rem,92%)] border-l border-[var(--ht-line)] bg-[var(--ht-surface-1)]/95 p-4 shadow-xl backdrop-blur-sm">
        <div className="flex items-start justify-between gap-3">
          <div><p className="ht-eyebrow">Selected anatomy</p><h2 className="mt-1 text-lg font-semibold text-ink">Unavailable component</h2></div>
          <button type="button" aria-label="Close component inspector" onClick={onClose} className="ht-btn ht-btn-ghost"><X size={16} /></button>
        </div>
        <p className="mt-5 text-sm leading-relaxed text-muted">This selection is not present in the current semantic registry.</p>
      </aside>
    );
  }

  return <InspectorContent report={model.report} knowledge={model.knowledge} patientState={model.patientState} onClose={onClose} onReport={onReport} />;
}
