import type { ComponentReport as ComponentReportModel } from "@/lib/heart/contracts";

function Section({ title, lines }: { title: string; lines: readonly string[] }) {
  return (
    <section className="border-t border-[var(--ht-line)] py-3 first:border-t-0">
      <h3 className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-muted">{title}</h3>
      <ul className="mt-2 space-y-1 text-xs leading-relaxed text-ink-2">
        {lines.map((line) => <li key={line}>{line}</li>)}
      </ul>
    </section>
  );
}

export function ComponentReport({ report }: { report: ComponentReportModel | null }) {
  if (!report) return null;
  const { component, knowledge, patientState } = report;
  return (
    <article aria-label={`${component.displayName} component report`} className="ht-panel overflow-hidden rounded-[var(--ht-r-md)]">
      <header className="border-b border-[var(--ht-line)] px-4 py-3">
        <p className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-muted">Component report</p>
        <h2 className="mt-1 text-base font-semibold text-ink">{component.displayName}</h2>
        <p className="mt-1 text-xs text-muted">{component.category.replace("_", " ")}</p>
      </header>
      <div className="grid gap-4 p-4 md:grid-cols-2">
        <section aria-labelledby="anatomy-report-heading">
          <h3 id="anatomy-report-heading" className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-[var(--ht-accent-bright)]">General anatomy</h3>
          <p className="mt-2 text-sm leading-relaxed text-ink-2">{knowledge.shortDescription}</p>
          <p className="mt-2 text-xs leading-relaxed text-muted">Normal function: {knowledge.primaryFunction}</p>
        </section>
        <section aria-labelledby="patient-state-heading">
            <h3 id="patient-state-heading" className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-[var(--ht-signal-bright)]">Current twin state</h3>
          <p className="mt-2 text-xs text-muted">
            Status: <span className="text-ink-2">{patientState.statusLabel.replace("_", " ")}</span>
          </p>
          {patientState.available ? null : <p className="mt-2 text-xs leading-relaxed text-muted">No patient-specific state is available for this component.</p>}
        </section>
      </div>
      <div className="px-4 pb-3">
        {report.sections.slice(2).map((section) => <Section key={section.id} title={section.title} lines={section.lines} />)}
        <p className="border-t border-[var(--ht-line)] pt-3 text-[0.68rem] leading-relaxed text-muted">{report.safetyNotice}</p>
      </div>
    </article>
  );
}

export default ComponentReport;
