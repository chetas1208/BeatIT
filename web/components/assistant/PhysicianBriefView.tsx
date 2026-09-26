"use client";

/*
 * CONTRACT: the one FULL detail-view implementation this wave — renders a real
 *   `DecisionSupportBundle` payload (python/hearttwin/assistant/physician_brief.py)
 *   inside a PHYSICIAN_BRIEF AssistantArtifact.
 *
 * Transparency rule (GLOBAL_ARCHITECTURE.md "PHYSICIAN SUPPORT ARCHITECTURE" /
 *   physician_brief.py's own docstrings): several DecisionSupportBundle lists
 *   are honestly empty today (missing_evidence, conflicts,
 *   possible_interpretations, and observed_evidence/simulated_results/
 *   uncertainty when no ensemble backs the case) — that means "not yet
 *   computable", not "nothing here". Every section below always renders,
 *   with an explicit empty-state sentence when its list is empty, instead of
 *   hiding the section. Do not add a "Recommended treatment" section or any
 *   treatment-shaped label anywhere in this file — DecisionSupportBundle has
 *   no such field, by design (no clinical decision authority in this layer).
 */

import type { ReactNode } from "react";
import {
  ClipboardText,
  Eye,
  Flask,
  Gauge,
  ListChecks,
  Question,
  Ruler,
  Scales,
  WarningCircle,
} from "@phosphor-icons/react";
import type { AssistantArtifact, ProvenanceRef } from "./ArtifactCard";

// ---------------------------------------------------------------------------
// DecisionSupportBundle mirror (python/hearttwin/assistant/physician_brief.py).
// Field list is verbatim from that module — do not add fields, especially not
// anything recommendation-shaped.
// ---------------------------------------------------------------------------

export interface DecisionSupportBundle {
  question?: string | null;
  clinical_context: Record<string, unknown>;
  observed_evidence: Record<string, unknown>[];
  derived_evidence: Record<string, unknown>[];
  simulated_results: Record<string, unknown>[];
  uncertainty: Record<string, unknown>[];
  missing_evidence: Record<string, unknown>[];
  conflicts: Record<string, unknown>[];
  assumptions: string[];
  provenance: ProvenanceRef[];
  limitations: string[];
  possible_interpretations: Record<string, unknown>[];
}

function asBundle(payload: Record<string, unknown>): DecisionSupportBundle {
  const arr = (key: string): Record<string, unknown>[] =>
    Array.isArray(payload[key]) ? (payload[key] as Record<string, unknown>[]) : [];
  const strArr = (key: string): string[] =>
    Array.isArray(payload[key]) ? (payload[key] as unknown[]).filter((v): v is string => typeof v === "string") : [];

  return {
    question: typeof payload.question === "string" ? payload.question : null,
    clinical_context:
      payload.clinical_context && typeof payload.clinical_context === "object"
        ? (payload.clinical_context as Record<string, unknown>)
        : {},
    observed_evidence: arr("observed_evidence"),
    derived_evidence: arr("derived_evidence"),
    simulated_results: arr("simulated_results"),
    uncertainty: arr("uncertainty"),
    missing_evidence: arr("missing_evidence"),
    conflicts: arr("conflicts"),
    assumptions: strArr("assumptions"),
    provenance: arr("provenance") as unknown as ProvenanceRef[],
    limitations: strArr("limitations"),
    possible_interpretations: arr("possible_interpretations"),
  };
}

// ---------------------------------------------------------------------------
// Small rendering helpers.
// ---------------------------------------------------------------------------

/** Renders a record's own fields as a compact key: value line, skipping nulls. */
function EntryLine({ entry }: { entry: Record<string, unknown> }) {
  const fields = Object.entries(entry).filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (fields.length === 0) {
    return <span className="text-muted">(empty entry)</span>;
  }
  return (
    <span className="text-ink-2">
      {fields.map(([key, value], i) => (
        <span key={key}>
          {i > 0 ? <span className="text-muted"> · </span> : null}
          <span className="text-muted">{key}: </span>
          {Array.isArray(value) ? value.join(", ") : String(value)}
        </span>
      ))}
    </span>
  );
}

function EntryList({ entries }: { entries: Record<string, unknown>[] }) {
  return (
    <ul className="space-y-1.5">
      {entries.map((entry, i) => (
        <li
          key={i}
          className="rounded-[var(--ht-r-sm)] border border-[var(--ht-line)] bg-surface-2/50 px-2.5 py-1.5 text-[0.78rem] leading-relaxed"
        >
          <EntryLine entry={entry} />
        </li>
      ))}
    </ul>
  );
}

function StringList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5">
      {items.map((text, i) => (
        <li
          key={i}
          className="rounded-[var(--ht-r-sm)] border border-[var(--ht-line)] bg-surface-2/50 px-2.5 py-1.5 text-[0.78rem] leading-relaxed text-ink-2"
        >
          {text}
        </li>
      ))}
    </ul>
  );
}

/** Every section renders unconditionally — empty is a fact to show, not to hide. */
function Section({
  icon: IconCmp,
  title,
  count,
  emptyLabel,
  children,
}: {
  icon: typeof ClipboardText;
  title: string;
  count: number;
  emptyLabel: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2">
        <IconCmp weight="regular" aria-hidden className="size-3.5 flex-none text-muted" />
        <h3 className="ht-eyebrow">{title}</h3>
        <span className="ht-chip" data-status={count > 0 ? "idle" : "warning"}>
          {count > 0 ? count : "none"}
        </span>
      </div>
      {count > 0 ? children : <p className="text-[0.78rem] italic text-muted">{emptyLabel}</p>}
    </section>
  );
}

// ---------------------------------------------------------------------------
// The view.
// ---------------------------------------------------------------------------

export function PhysicianBriefView({ artifact }: { artifact: AssistantArtifact }) {
  const bundle = asBundle(artifact.payload);

  return (
    <div className="space-y-5">
      <div>
        <p className="ht-eyebrow">Physician decision support</p>
        <h2 className="mt-1 text-lg font-semibold text-ink">
          {bundle.question ?? artifact.title}
        </h2>
        {Object.keys(bundle.clinical_context).length > 0 ? (
          <p className="mt-1 text-[0.78rem] text-muted">
            {Object.entries(bundle.clinical_context)
              .filter(([, v]) => v !== null && v !== undefined && v !== "")
              .map(([k, v]) => `${k}: ${String(v)}`)
              .join(" · ")}
          </p>
        ) : null}
      </div>

      <Section
        icon={Eye}
        title="Observed evidence"
        count={bundle.observed_evidence.length}
        emptyLabel="None identified — no directly-observed (non-computed) values are available from today's tool coverage. See Limitations."
      >
        <EntryList entries={bundle.observed_evidence} />
      </Section>

      <Section
        icon={ListChecks}
        title="Derived evidence"
        count={bundle.derived_evidence.length}
        emptyLabel="None identified."
      >
        <EntryList entries={bundle.derived_evidence} />
      </Section>

      <Section
        icon={Flask}
        title="Simulated results"
        count={bundle.simulated_results.length}
        emptyLabel="Not yet available — no ensemble run backs this brief."
      >
        <EntryList entries={bundle.simulated_results} />
      </Section>

      <Section
        icon={Gauge}
        title="Uncertainty"
        count={bundle.uncertainty.length}
        emptyLabel="Not yet available — no ensemble run backs this brief."
      >
        <EntryList entries={bundle.uncertainty} />
      </Section>

      <Section
        icon={Ruler}
        title="Assumptions"
        count={bundle.assumptions.length}
        emptyLabel="None recorded."
      >
        <StringList items={bundle.assumptions} />
      </Section>

      <Section
        icon={WarningCircle}
        title="Missing evidence"
        count={bundle.missing_evidence.length}
        emptyLabel="Not yet computable — no evidence-completeness analysis exists yet. This does not mean nothing is missing."
      >
        <EntryList entries={bundle.missing_evidence} />
      </Section>

      <Section
        icon={Scales}
        title="Conflicts"
        count={bundle.conflicts.length}
        emptyLabel="Not yet checked — no cross-source conflict detection exists yet. This does not mean no conflicts exist."
      >
        <EntryList entries={bundle.conflicts} />
      </Section>

      <Section
        icon={Question}
        title="Possible interpretations"
        count={bundle.possible_interpretations.length}
        emptyLabel="Not enumerated — this brief presents evidence for the physician to interpret; it does not rank interpretations itself."
      >
        <EntryList entries={bundle.possible_interpretations} />
      </Section>

      <Section
        icon={WarningCircle}
        title="Limitations"
        count={bundle.limitations.length}
        emptyLabel="None recorded."
      >
        <StringList items={bundle.limitations} />
      </Section>
    </div>
  );
}
