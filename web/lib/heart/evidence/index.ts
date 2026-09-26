import type { CardiacTwinState, SourceMapEntry, ValueSource } from "@/types/heart";
import type { ComponentEvidence, EvidenceKind } from "@/lib/heart/contracts";
import { HeartComponentRegistry } from "@/lib/heart/registry";

export interface EvidenceKindMetadata {
  label: string;
  description: string;
  className: string;
}

export const EVIDENCE_KIND_METADATA: Record<EvidenceKind, EvidenceKindMetadata> = {
  directly_observed: {
    label: "Directly observed",
    description: "Entered as a patient or operator observation.",
    className: "border-[var(--ht-signal)] bg-[var(--ht-signal)]/10 text-[var(--ht-signal-bright)]",
  },
  extracted: {
    label: "Extracted",
    description: "Read from an uploaded source by the extraction pipeline.",
    className: "border-[var(--ht-accent)] bg-[var(--ht-accent)]/10 text-[var(--ht-accent-bright)]",
  },
  derived: {
    label: "Derived",
    description: "Computed from other evidence by the deterministic model.",
    className: "border-amber-400/40 bg-amber-400/10 text-amber-200",
  },
  default_model_prior: {
    label: "Model prior",
    description: "Filled from a model prior because direct evidence was unavailable.",
    className: "border-violet-400/40 bg-violet-400/10 text-violet-200",
  },
  simulated: {
    label: "Simulated",
    description: "Produced by a bounded simulation, not an observation.",
    className: "border-cyan-400/40 bg-cyan-400/10 text-cyan-200",
  },
  unavailable: {
    label: "Unavailable",
    description: "No supporting provenance is available for this value.",
    className: "border-[var(--ht-line)] bg-[var(--ht-surface-2)] text-muted",
  },
};

export function evidenceKind(source: string | ValueSource | null | undefined): EvidenceKind {
  switch (source?.trim().toLowerCase()) {
    case "file_extraction":
    case "extracted":
    case "extraction":
      return "extracted";
    case "user_input":
    case "directly_observed":
    case "observed":
      return "directly_observed";
    case "derived":
      return "derived";
    case "default_model_prior":
    case "model_prior":
    case "prior":
      return "default_model_prior";
    case "simulated":
    case "simulation":
      return "simulated";
    default:
      return "unavailable";
  }
}

export function evidenceKindMetadata(kind: EvidenceKind): EvidenceKindMetadata {
  return EVIDENCE_KIND_METADATA[kind];
}

function fieldMatchesBinding(field: string, binding: string): boolean {
  const normalizedField = field.replace(/^.*\./, "");
  return normalizedField === binding || field === binding;
}

function labelForField(field: string): string {
  return field
    .split(".")
    .at(-1)!
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function sourceMapEntryToEvidence(entry: SourceMapEntry, id = `source:${entry.field}`): ComponentEvidence {
  return {
    id,
    label: labelForField(entry.field),
    kind: evidenceKind(entry.source),
    source: entry.source_file_id ?? entry.source,
    method: entry.method ?? undefined,
    timestamp: undefined,
    confidence: Number.isFinite(entry.confidence) ? entry.confidence : undefined,
    derivation: entry.evidence ?? undefined,
  };
}

export function getComponentEvidence(componentId: string, state: CardiacTwinState | null | undefined): ComponentEvidence[] {
  const definition = HeartComponentRegistry.getComponent(componentId);
  if (!definition || !state) return [];
  return state.source_map
    .filter((entry) => definition.physiologyBindings.some((binding) => fieldMatchesBinding(entry.field, binding)))
    .map((entry, index) => sourceMapEntryToEvidence(entry, `${componentId}-evidence-${index}`));
}

export function groupEvidenceByKind(evidence: readonly ComponentEvidence[]): ReadonlyMap<EvidenceKind, readonly ComponentEvidence[]> {
  const groups = new Map<EvidenceKind, ComponentEvidence[]>();
  for (const entry of evidence) {
    const group = groups.get(entry.kind) ?? [];
    group.push(entry);
    groups.set(entry.kind, group);
  }
  return groups;
}
