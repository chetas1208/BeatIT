"use client";

import { FileText } from "@phosphor-icons/react";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/Panel";
import { useDualBeatStore } from "@/lib/store";
import { useTemporalTwin } from "@/lib/twin/integration/context";
import { useScenario } from "@/lib/twin/scenario/useScenario";
import { useComparisonStore } from "@/lib/twin/comparison/store";
import { buildProductReport } from "@/lib/product/reportContracts";
import type { BeatITSessionContext } from "@/lib/product/contracts";
import { SourceStatusBadge } from "@/components/product/SourceStatusBadge";

export function ReportSurface({ context }: { context: BeatITSessionContext }) {
  const state = useDualBeatStore((s) => s.state);
  const visualization = useDualBeatStore((s) => s.visualization);
  const disclaimer = useDualBeatStore((s) => s.safetyDisclaimer);
  const scenario = useScenario();
  const temporal = useTemporalTwin();
  const comparison = useComparisonStore((s) => s.paired);
  const reportContext: BeatITSessionContext = {
    ...context,
    snapshotId: context.snapshotId ?? temporal.selectedSnapshot?.id ?? null,
    ensembleId: context.ensembleId ?? scenario.ensemble?.id ?? null,
    scenarioId: context.scenarioId ?? scenario.result?.definition.id ?? null,
  };
  const report = buildProductReport({
    context: reportContext,
    safetyDisclaimer: disclaimer,
    hasState: Boolean(state),
    hasVisualization: Boolean(visualization),
    hasTimeline: Boolean(temporal.timeline),
    hasExperiment: Boolean(scenario.result || scenario.ensemble),
    hasComparison: Boolean(comparison),
    hasEvidence: Boolean(scenario.ensemble),
    provenance: [temporal.selectedSnapshot?.id, scenario.ensemble?.id, comparison?.pairId].filter((id): id is string => Boolean(id)),
  });

  return (
    <Panel className="h-full overflow-y-auto" raised>
      <PanelHeader icon={FileText} title={report.title} eyebrow="REPORT" accent="signal" />
      <PanelBody>
        <div className="border border-warn/50 bg-warn/10 px-3 py-2 text-xs text-ink-2"><strong>Educational simulation only.</strong> {report.safetyDisclaimer}</div>
        <div className="mt-3 flex flex-wrap items-center gap-1.5" aria-label="Source status legend">
          <span className="text-[0.62rem] text-muted">Data status:</span>
          {(["observed", "derived", "simulated", "prior", "synthetic"] as const).map((status) => <SourceStatusBadge key={status} status={status} />)}
        </div>
        <p className="mt-3 text-xs leading-relaxed text-muted">This report is assembled from the active session. It keeps unavailable sections visible so missing evidence is not mistaken for a result.</p>
        <div className="mt-4 space-y-2">
          {report.sections.map((section) => (
            <section key={section.id} className="border border-[var(--ht-line)] px-3 py-2.5" aria-labelledby={`report-${section.id}`}>
              <div className="flex flex-wrap items-center justify-between gap-2"><h3 id={`report-${section.id}`} className="text-sm font-semibold text-ink">{section.title}</h3><span className="ht-chip" data-status={section.status === "ready" ? "success" : "warning"}>{section.status}</span></div>
              <p className="mt-1 text-xs leading-relaxed text-muted">{section.summary}</p>
              {section.provenance.length > 0 ? <p className="mt-1 text-[0.62rem] text-muted">Source IDs: {section.provenance.join(", ")}</p> : null}
            </section>
          ))}
        </div>
        <section className="mt-4 border border-[var(--ht-line)] px-3 py-2.5" aria-labelledby="report-limitations">
          <h3 id="report-limitations" className="text-sm font-semibold text-ink">Interpretation boundaries</h3>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-relaxed text-muted">{report.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
        </section>
      </PanelBody>
    </Panel>
  );
}
