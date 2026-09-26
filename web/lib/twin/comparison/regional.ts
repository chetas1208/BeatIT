import type { CardiacFinding } from "@/types/heart";

/** The only segment identifiers accepted by the existing AHA-17 finding layer. */
export const AHA_SEGMENT_MIN = 1;
export const AHA_SEGMENT_MAX = 17;

export type RegionalAvailability = "available" | "unavailable";

/**
 * A finding reference copied from the backend. It is evidence for a mapping,
 * not a newly inferred anatomical claim.
 */
export interface RegionalFindingEvidence {
  readonly id: string;
  readonly region: string;
  readonly territory: string | null;
  readonly ahaSegments: readonly number[];
  readonly source: string;
}

/**
 * An explicitly supplied regional delta. This module never derives one from
 * severity, metric text, or scalar M6 differences.
 */
export interface ExplicitRegionalDelta {
  readonly value: number;
  readonly unit: string;
  readonly source: string;
  readonly evidence: readonly string[];
}

export interface RegionalDifference {
  readonly findingId: string;
  readonly baseline: RegionalFindingEvidence | null;
  readonly scenario: RegionalFindingEvidence | null;
  /** Shared AHA segments only when both explicit findings agree. */
  readonly ahaSegments: readonly number[];
  readonly mappingAvailability: RegionalAvailability;
  readonly deltaAvailability: RegionalAvailability;
  readonly delta: ExplicitRegionalDelta | null;
  readonly evidence: readonly string[];
  readonly limitation: string;
}

export interface RegionalDifferenceInput {
  readonly baselineFindings: readonly CardiacFinding[];
  readonly scenarioFindings: readonly CardiacFinding[];
  /** Optional, externally computed evidence keyed by the exact finding ID. */
  readonly explicitDeltas?: Readonly<Record<string, ExplicitRegionalDelta | null>>;
}

const REGIONAL_FINDING_PREFIX = "regional_";
const NO_DELTA_LIMITATION =
  "No explicit regional delta was supplied; scalar differences are not localized to anatomy.";
const UNAVAILABLE_LIMITATION =
  "AHA regional comparison is unavailable because paired explicit finding evidence is incomplete or inconsistent.";

function text(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  return normalized || null;
}

function normalizeSegments(value: unknown): readonly number[] | null {
  if (!Array.isArray(value) || value.length === 0) return null;

  const segments = value.map((segment) => {
    if (typeof segment !== "number" || !Number.isInteger(segment)) return null;
    return segment >= AHA_SEGMENT_MIN && segment <= AHA_SEGMENT_MAX ? segment : null;
  });
  if (segments.some((segment) => segment === null)) return null;

  const numericSegments = segments as number[];
  if (new Set(numericSegments).size !== numericSegments.length) return null;
  return [...numericSegments].sort((a, b) => a - b);
}

function sameSegments(left: readonly number[], right: readonly number[]): boolean {
  return left.length === right.length && left.every((segment, index) => segment === right[index]);
}

function isRegionalId(id: string | null): boolean {
  return id?.startsWith(REGIONAL_FINDING_PREFIX) ?? false;
}

function findingEvidence(finding: CardiacFinding | null | undefined): RegionalFindingEvidence | null {
  if (!finding) return null;
  const id = text(finding.id);
  const region = text(finding.region);
  const source = text(finding.source);
  const ahaSegments = normalizeSegments(finding.aha_segments);
  if (!id || !isRegionalId(id) || !region || !source || !ahaSegments) return null;

  return {
    id,
    region,
    territory: text(finding.territory),
    ahaSegments,
    source,
  };
}

function validDelta(value: ExplicitRegionalDelta | null | undefined): ExplicitRegionalDelta | null {
  if (!value || typeof value !== "object") return null;
  const unit = text(value.unit);
  const source = text(value.source);
  const evidence = Array.isArray(value.evidence)
    ? value.evidence.map((item) => text(item)).filter((item): item is string => item !== null)
    : [];
  if (typeof value.value !== "number" || !Number.isFinite(value.value) || !unit || !source || evidence.length === 0) {
    return null;
  }
  return { value: value.value, unit, source, evidence: [...new Set(evidence)] };
}

function candidateId(
  baseline: CardiacFinding | null | undefined,
  scenario: CardiacFinding | null | undefined,
): string {
  return text(baseline?.id) ?? text(scenario?.id) ?? "unavailable";
}

/**
 * Compare one pair of findings without inventing regional physiology.
 *
 * A mapping is available only when both sides carry the same explicit
 * `regional_*` finding ID, valid AHA-17 segments, and the same segment set.
 * A numeric delta is copied only when the caller supplies separately sourced
 * regional evidence; it is never calculated from the finding payload.
 */
export function buildRegionalDifference(
  baseline: CardiacFinding | null | undefined,
  scenario: CardiacFinding | null | undefined,
  explicitDelta?: ExplicitRegionalDelta | null,
): RegionalDifference {
  const baselineEvidence = findingEvidence(baseline);
  const scenarioEvidence = findingEvidence(scenario);
  const findingId = candidateId(baseline, scenario);
  const evidence: string[] = [];
  const baselineId = text(baseline?.id);
  const scenarioId = text(scenario?.id);

  if (baselineEvidence) {
    evidence.push(
      `Baseline finding ${baselineEvidence.id} explicitly declares AHA segments ${baselineEvidence.ahaSegments.join(", ")}.`,
    );
  }
  if (scenarioEvidence) {
    evidence.push(
      `Scenario finding ${scenarioEvidence.id} explicitly declares AHA segments ${scenarioEvidence.ahaSegments.join(", ")}.`,
    );
  }

  const idsMatch = baselineEvidence !== null
    && scenarioEvidence !== null
    && baselineEvidence.id === scenarioEvidence.id
    && baselineId === scenarioId;
  const regionsMatch = idsMatch && baselineEvidence.region === scenarioEvidence.region;
  const segmentsMatch = idsMatch
    && regionsMatch
    && sameSegments(baselineEvidence.ahaSegments, scenarioEvidence.ahaSegments);
  const mappingAvailability: RegionalAvailability = segmentsMatch ? "available" : "unavailable";

  if (idsMatch && !regionsMatch) {
    evidence.push("Baseline and scenario findings use different regional labels; no shared AHA mapping is reported.");
  } else if (idsMatch && !segmentsMatch) {
    evidence.push("Baseline and scenario findings use different AHA segment sets; no shared regional mapping is reported.");
  } else if (!idsMatch) {
    evidence.push("AHA regional mapping requires the same explicit regional finding ID on baseline and scenario.");
  }

  const delta = validDelta(explicitDelta);
  const deltaAvailability: RegionalAvailability = mappingAvailability === "available" && delta ? "available" : "unavailable";
  if (delta) {
    evidence.push(...delta.evidence);
  } else {
    evidence.push(NO_DELTA_LIMITATION);
  }

  return {
    findingId,
    baseline: baselineEvidence,
    scenario: scenarioEvidence,
    ahaSegments: segmentsMatch ? [...baselineEvidence.ahaSegments] : [],
    mappingAvailability,
    deltaAvailability,
    delta,
    evidence,
    limitation: mappingAvailability === "available" && deltaAvailability === "available"
      ? "Regional values are educational simulation evidence and remain limited to the supplied finding mapping."
      : mappingAvailability === "available"
        ? NO_DELTA_LIMITATION
        : UNAVAILABLE_LIMITATION,
  };
}

function findingsById(findings: readonly CardiacFinding[]): Map<string, CardiacFinding[]> {
  const grouped = new Map<string, CardiacFinding[]>();
  for (const finding of findings) {
    const id = text(finding?.id);
    if (!id || !isRegionalId(id)) continue;
    const existing = grouped.get(id) ?? [];
    existing.push(finding);
    grouped.set(id, existing);
  }
  return grouped;
}

/** Build stable regional comparison rows from the paired finding collections. */
export function buildRegionalDifferences(input: RegionalDifferenceInput): readonly RegionalDifference[] {
  const baseline = findingsById(input.baselineFindings);
  const scenario = findingsById(input.scenarioFindings);
  const ids = new Set([...baseline.keys(), ...scenario.keys()]);

  return [...ids].sort().map((findingId) => {
    const baselineMatches = baseline.get(findingId) ?? [];
    const scenarioMatches = scenario.get(findingId) ?? [];
    const duplicate = baselineMatches.length > 1 || scenarioMatches.length > 1;
    const result = buildRegionalDifference(
      baselineMatches[0],
      scenarioMatches[0],
      input.explicitDeltas?.[findingId],
    );
    if (!duplicate) return result;

    return {
      ...result,
      mappingAvailability: "unavailable",
      deltaAvailability: "unavailable",
      ahaSegments: [],
      delta: null,
      evidence: [...result.evidence, "Duplicate regional finding IDs make the paired evidence ambiguous."],
      limitation: UNAVAILABLE_LIMITATION,
    };
  });
}
