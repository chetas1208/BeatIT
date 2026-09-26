import type {
  AnatomyKnowledge,
  ComponentEvidence,
  ComponentReport,
  PatientBindingInput,
  PatientComponentState,
} from "@/lib/heart/contracts";
import { HeartComponentRegistry, HEART_COMPONENTS, type HeartComponentDefinition } from "@/lib/heart/registry";
import type {
  CardiacFinding,
  CardiacFindings,
  CardiacTwinState,
  MeasuredValue,
  SourceMapEntry,
  ValueSource,
} from "@/types/heart";

type ComponentMetric = PatientComponentState["metrics"][number];

const SAFETY_NOTICE =
  "Educational simulation observations with reference cardiology terminology. Not a diagnosis, treatment recommendation, medication recommendation, or emergency guidance.";

const SECTION_TITLES: Record<ComponentReport["sections"][number]["id"], string> = {
  structure: "Structure",
  function: "Function",
  electrical: "Electrical",
  hemodynamics: "Hemodynamics",
  regional_findings: "Regional findings",
  evidence: "Evidence",
  limitations: "Limitations",
};

function isMeasuredValue(value: unknown): value is MeasuredValue {
  return Boolean(
    value &&
      typeof value === "object" &&
      typeof (value as MeasuredValue).value === "number" &&
      Number.isFinite((value as MeasuredValue).value),
  );
}

function sourceKind(source: ValueSource | undefined): ComponentEvidence["kind"] {
  switch (source) {
    case "file_extraction":
      return "extracted";
    case "user_input":
      return "directly_observed";
    case "derived":
      return "derived";
    case "default_model_prior":
      return "default_model_prior";
    default:
      return "unavailable";
  }
}

function readField(state: CardiacTwinState, field: string): unknown {
  const sections: readonly Record<string, unknown>[] = [
    state.measurements as Record<string, unknown>,
    state.electrophysiology as Record<string, unknown>,
    state.hemodynamics as Record<string, unknown>,
    state.tissue_state as Record<string, unknown>,
  ];

  for (const section of sections) {
    if (field in section) return section[field];
  }
  return undefined;
}

function labelForField(field: string): string {
  return field
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatValue(value: MeasuredValue): string {
  return `${value.value} ${value.unit}`.trim();
}

function sourceEntryFor(entries: readonly SourceMapEntry[], field: string): SourceMapEntry | undefined {
  return entries.find((entry) => entry.field === field);
}

function metricForField(state: CardiacTwinState, field: string, entry?: SourceMapEntry): ComponentMetric | null {
  const value = readField(state, field);
  if (isMeasuredValue(value)) {
    return {
      label: labelForField(field),
      value: formatValue(value),
      sourceKind: sourceKind(entry?.source ?? value.source),
    };
  }

  if (typeof value === "string" && value.trim()) {
    return {
      label: labelForField(field),
      value,
      sourceKind: sourceKind(entry?.source),
    };
  }

  return null;
}

function evidenceForEntry(entry: SourceMapEntry): ComponentEvidence {
  return {
    id: `source:${entry.field}`,
    label: labelForField(entry.field),
    kind: sourceKind(entry.source),
    source: entry.source_file_id ?? entry.source,
    ...(entry.method ? { method: entry.method } : {}),
    ...(typeof entry.confidence === "number" ? { confidence: entry.confidence } : {}),
    ...(entry.evidence ? { derivation: entry.evidence } : {}),
  };
}

function evidenceForFinding(finding: CardiacFinding): ComponentEvidence {
  return {
    id: `finding:${finding.id}`,
    label: finding.title,
    kind: "derived",
    source: finding.source,
    derivation: finding.summary,
  };
}

function findingMatchesComponent(finding: CardiacFinding, component: HeartComponentDefinition): boolean {
  if (component.id === "left-ventricle" && finding.id === "global_systolic") return true;
  return HeartComponentRegistry.getComponentsForFinding(finding).some((candidate) => candidate.id === component.id);
}

function findingsForComponent(findings: CardiacFindings | null | undefined, component: HeartComponentDefinition): CardiacFinding[] {
  return (findings?.findings ?? []).filter((finding) => finding.id !== "global_systolic" && findingMatchesComponent(finding, component));
}

function relatedComponentIds(component: HeartComponentDefinition): string[] {
  const related = new Set<string>();
  const parentId = component.anatomy.parentId;
  if (parentId) related.add(parentId);

  for (const candidate of HEART_COMPONENTS) {
    if (candidate.id === component.id) continue;
    if (component.ahaSegment !== undefined && candidate.ahaSegment === component.ahaSegment) related.add(candidate.id);
    if (component.coronaryTerritory && candidate.coronaryTerritory === component.coronaryTerritory) related.add(candidate.id);
  }

  return [...related];
}

function statusFor(metrics: readonly ComponentMetric[], evidence: readonly ComponentEvidence[], findings: readonly CardiacFinding[]): PatientComponentState["statusLabel"] {
  const kinds = [...metrics.map((metric) => metric.sourceKind), ...evidence.map((item) => item.kind)];
  if (kinds.some((kind) => kind === "directly_observed" || kind === "extracted")) return "observed";
  if (kinds.includes("derived") || findings.length > 0) return "derived";
  if (kinds.includes("default_model_prior")) return "prior";
  if (kinds.includes("simulated")) return "simulated";
  return "insufficient_evidence";
}

function limitationsFor(
  state: CardiacTwinState | null | undefined,
  component: HeartComponentDefinition,
  metrics: readonly ComponentMetric[],
  findings: readonly CardiacFinding[],
): string[] {
  const limitations: string[] = [];
  if (!state) limitations.push("No CardiacTwinState was provided.");
  if (state && metrics.length === 0 && findings.length === 0) {
    limitations.push(`No patient-specific evidence is available for ${component.displayName}.`);
  }
  if (state && component.physiologyBindings.length > metrics.length) {
    limitations.push("Some registered physiological quantities are not present in the current state.");
  }
  if (state && state.data_quality_score < 1) {
    limitations.push(`State data-quality score: ${state.data_quality_score}.`);
  }
  return limitations;
}

function anatomyKnowledge(component: HeartComponentDefinition): AnatomyKnowledge {
  return {
    componentId: component.id,
    name: component.displayName,
    shortDescription: component.anatomy.description,
    primaryFunction: component.anatomy.description,
    relatedStructures: relatedComponentIds(component),
    physiologyConcepts: component.physiologyBindings,
  };
}

export function buildPatientComponentState(
  component: HeartComponentDefinition,
  input: PatientBindingInput,
): PatientComponentState {
  const state = input.state;
  const sourceMap = state?.source_map ?? [];
  const metrics = state
    ? component.physiologyBindings
        .map((field) => metricForField(state, field, sourceEntryFor(sourceMap, field)))
        .filter((metric): metric is ComponentMetric => metric !== null)
    : [];
  const findings = findingsForComponent(input.findings, component);
  const evidence = component.physiologyBindings
    .map((field) => sourceEntryFor(sourceMap, field))
    .filter((entry): entry is SourceMapEntry => entry !== undefined)
    .map(evidenceForEntry);
  evidence.push(...findings.map(evidenceForFinding));

  return {
    componentId: component.id,
    available: metrics.length > 0 || findings.length > 0,
    statusLabel: statusFor(metrics, evidence, findings),
    metrics,
    findings,
    evidence,
    limitations: limitationsFor(state, component, metrics, findings),
    relatedComponentIds: relatedComponentIds(component),
  };
}

export function buildPatientComponentStates(input: PatientBindingInput): readonly PatientComponentState[] {
  return HEART_COMPONENTS.map((component) => buildPatientComponentState(component, input));
}

export function getPatientComponentState(
  componentId: string,
  input: PatientBindingInput,
): PatientComponentState | undefined {
  const component = HeartComponentRegistry.getComponent(componentId);
  return component ? buildPatientComponentState(component, input) : undefined;
}

function section(
  id: ComponentReport["sections"][number]["id"],
  lines: readonly string[],
): ComponentReport["sections"][number] {
  return { id, title: SECTION_TITLES[id], lines };
}

export function buildComponentReport(
  componentId: string,
  input: PatientBindingInput,
): ComponentReport | undefined {
  const component = HeartComponentRegistry.getComponent(componentId);
  if (!component) return undefined;

  const patientState = buildPatientComponentState(component, input);
  const knowledge = anatomyKnowledge(component);
  const sections: Array<ComponentReport["sections"][number]> = [
    section("structure", [knowledge.shortDescription]),
    section("function", knowledge.physiologyConcepts.length > 0 ? knowledge.physiologyConcepts.map(labelForField) : ["No physiological binding is registered."]),
    section("evidence", patientState.evidence.length > 0 ? patientState.evidence.map((item) => item.label) : ["No source-map evidence is available."]),
  ];

  if (patientState.metrics.length > 0) {
    sections.push(section("hemodynamics", patientState.metrics.map((metric) => `${metric.label}: ${metric.value}`)));
  }
  if (patientState.findings.length > 0) {
    sections.push(section("regional_findings", patientState.findings.map((finding) => `${finding.title}: ${finding.summary}`)));
  }
  if (patientState.limitations.length > 0) {
    sections.push(section("limitations", patientState.limitations));
  }

  return { component, knowledge, patientState, sections, safetyNotice: input.findings?.disclaimer ?? SAFETY_NOTICE };
}

export const buildPatientComponentReport = buildComponentReport;
