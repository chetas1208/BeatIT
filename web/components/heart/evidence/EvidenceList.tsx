import type { ComponentEvidence } from "@/lib/heart/contracts";
import { evidenceKindMetadata, groupEvidenceByKind } from "@/lib/heart/evidence";

export function EvidenceList({ evidence }: { evidence: readonly ComponentEvidence[] }) {
  if (!evidence.length) {
    return (
      <p className="text-xs text-muted" role="status">
        No component-specific provenance is available.
      </p>
    );
  }

  const groups = groupEvidenceByKind(evidence);
  return (
    <div aria-label="Evidence provenance" className="space-y-4">
      {[...groups.entries()].map(([kind, entries]) => {
        const metadata = evidenceKindMetadata(kind);
        return (
          <section key={kind} aria-labelledby={`evidence-${kind}`}>
            <div className="flex items-center gap-2">
              <h3 id={`evidence-${kind}`} className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-muted">
                {metadata.label}
              </h3>
              <span className={`rounded-full border px-2 py-0.5 text-[0.62rem] ${metadata.className}`}>
                {entries.length}
              </span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted">{metadata.description}</p>
            <ul className="mt-2 space-y-2">
              {entries.map((entry) => (
                <li key={entry.id} className="border-l-2 border-[var(--ht-line)] pl-2 text-xs">
                  <div className="font-medium text-ink">{entry.label}</div>
                  <div className="text-muted">
                    {entry.source ?? "Source not specified"}
                    {entry.method ? ` · ${entry.method}` : ""}
                    {entry.confidence != null ? ` · confidence ${Math.round(entry.confidence * 100)}%` : ""}
                  </div>
                  {entry.derivation ? <p className="mt-1 leading-relaxed text-ink-2">{entry.derivation}</p> : null}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
