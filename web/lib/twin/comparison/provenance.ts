import type {
  ShadowTrialPair,
  ShadowTrialResponse,
  ShadowTrialScenarioParameter,
} from "@/types/shadow-trial";

/** The M6 records that can be projected without adding a new causal claim. */
export type ComparisonTraceStepKind =
  | "origin_snapshot"
  | "baseline_ensemble"
  | "scenario_definition"
  | "baseline_twin"
  | "scenario_twin"
  | "paired_comparison"
  | "paired_delta";

export interface ComparisonTraceLineage {
  readonly originSnapshotId: string | null;
  readonly baselineEnsembleId: string;
  readonly scenarioId: string;
  readonly pairingPolicy: string | null;
  readonly pairs: readonly ComparisonPairLineage[];
}

export interface ComparisonPairLineage {
  readonly sampleId: string;
  readonly baselineTwinId: string;
  readonly scenarioTwinId: string;
  readonly baselineParameters: Readonly<Record<string, number>>;
  readonly scenarioParameters: Readonly<Record<string, number>>;
  readonly parameters: Readonly<Record<string, number>>;
  readonly valid: boolean;
  readonly rejectionReasons: readonly string[];
}

export interface ComparisonTraceStep {
  /** Stable ID derived only from the M6 identifiers and metric ID. */
  readonly id: string;
  readonly kind: ComparisonTraceStepKind;
  readonly label: string;
  /** Existing lineage dependencies; no formula or physiological step is inferred. */
  readonly parentIds: readonly string[];
  readonly evidenceIds: readonly string[];
  readonly lineage: Readonly<Record<string, string>>;
  readonly details: Readonly<Record<string, unknown>>;
}

export interface ComparisonCausalTrace {
  readonly id: string;
  readonly trialId: string;
  readonly status: ShadowTrialResponse["status"];
  readonly deterministic: true;
  readonly originSnapshotId: string | null;
  readonly baselineEnsembleId: string;
  readonly scenarioId: string;
  readonly pairIds: readonly string[];
  readonly evidenceIds: readonly string[];
  readonly provenance: Readonly<Record<string, unknown>>;
  readonly lineage: ComparisonTraceLineage;
  readonly steps: readonly ComparisonTraceStep[];
  readonly warnings: readonly string[];
  readonly safetyDisclaimer: string;
}

export interface ProjectComparisonTraceOptions {
  /** Project one pair; omit to project every retained M6 pair. */
  readonly pairId?: string;
  /** Invalid pairs remain in the trace by default so rejection lineage is not hidden. */
  readonly includeInvalidPairs?: boolean;
}

const EMPTY_EVIDENCE: readonly string[] = [];

function requiredId(value: string, field: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new RangeError(`M6 ${field} must be a non-empty string`);
  }
  return value;
}

function compareStrings(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function uniqueSorted(values: readonly string[]): readonly string[] {
  return [...new Set(values)].sort(compareStrings);
}

function sortedRecord<T>(record: Readonly<Record<string, T>>): Readonly<Record<string, T>> {
  return Object.fromEntries(
    Object.keys(record)
      .sort(compareStrings)
      .map((key) => [key, record[key]]),
  );
}

function canonicalValue(value: unknown, seen = new Set<object>()): unknown {
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) throw new TypeError("M6 provenance must not contain cycles");
  seen.add(value);

  if (Array.isArray(value)) {
    const result = value.map((entry) => canonicalValue(entry, seen));
    seen.delete(value);
    return result;
  }

  const result = Object.fromEntries(
    Object.keys(value as Record<string, unknown>)
      .sort(compareStrings)
      .map((key) => [key, canonicalValue((value as Record<string, unknown>)[key], seen)]),
  );
  seen.delete(value);
  return result;
}

function canonicalRecord(record: Readonly<Record<string, unknown>>): Readonly<Record<string, unknown>> {
  return canonicalValue(record) as Readonly<Record<string, unknown>>;
}

function scenarioParameters(
  response: ShadowTrialResponse,
): readonly ShadowTrialScenarioParameter[] {
  const parameters = response.definition?.scenario.parameters ?? [];
  return [...parameters].sort((a, b) => compareStrings(a.parameter, b.parameter));
}

function parameterRecord(
  parameters: Readonly<Record<string, number>> | undefined,
): Readonly<Record<string, number>> {
  return sortedRecord(parameters ?? {});
}

function step(
  value: ComparisonTraceStep,
): ComparisonTraceStep {
  return value;
}

function pairLineage(pair: ShadowTrialPair): ComparisonPairLineage {
  return {
    sampleId: pair.sample_id,
    baselineTwinId: pair.baseline_twin_id,
    scenarioTwinId: pair.scenario_twin_id,
    baselineParameters: parameterRecord(pair.baseline_parameters),
    scenarioParameters: parameterRecord(pair.scenario_parameters),
    parameters: parameterRecord(pair.parameters),
    valid: pair.valid,
    rejectionReasons: [...pair.rejection_reasons],
  };
}

function validatePair(pair: ShadowTrialPair): void {
  requiredId(pair.sample_id, "pair sample_id");
  requiredId(pair.baseline_twin_id, "pair baseline_twin_id");
  requiredId(pair.scenario_twin_id, "pair scenario_twin_id");
  if (pair.baseline_twin_id !== pair.sample_id) {
    throw new RangeError(
      `M6 pair ${pair.sample_id} must preserve baseline_twin_id as sample_id`,
    );
  }
  if (pair.scenario_twin_id === pair.baseline_twin_id) {
    throw new RangeError(`M6 pair ${pair.sample_id} must have distinct twin IDs`);
  }
  if (!pair.valid && pair.rejection_reasons.length === 0) {
    throw new RangeError(`M6 invalid pair ${pair.sample_id} must retain rejection reasons`);
  }
  if (pair.valid && pair.rejection_reasons.length > 0) {
    throw new RangeError(`M6 valid pair ${pair.sample_id} cannot retain rejection reasons`);
  }
}

function selectedPairs(
  response: ShadowTrialResponse,
  options: ProjectComparisonTraceOptions,
): readonly ShadowTrialPair[] {
  const pairs = [...response.paired_results];
  const seen = new Set<string>();
  for (const pair of pairs) {
    validatePair(pair);
    if (seen.has(pair.sample_id)) {
      throw new RangeError(`M6 paired results contain duplicate sample_id: ${pair.sample_id}`);
    }
    seen.add(pair.sample_id);
  }

  const selected = options.pairId === undefined
    ? pairs
    : pairs.filter((pair) => pair.sample_id === options.pairId);
  if (options.pairId !== undefined && selected.length === 0) {
    throw new RangeError(`M6 pair not found: ${options.pairId}`);
  }

  return selected
    .filter((pair) => options.includeInvalidPairs !== false || pair.valid)
    .sort((a, b) => compareStrings(a.sample_id, b.sample_id));
}

function freezeDeep<T>(value: T, seen = new WeakSet<object>()): T {
  if (value === null || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  for (const nested of Object.values(value)) freezeDeep(nested, seen);
  return Object.freeze(value);
}

/**
 * Project the authoritative M6 Shadow Trial lineage into a comparison trace.
 *
 * The projection is deliberately narrower than a physiology graph. It records
 * only relationships present in M6: origin, baseline ensemble, scenario
 * definition, same-sample twins, paired comparisons, and returned deltas.
 * In particular, it does not add parameter-to-organ or metric-to-outcome
 * steps, because those causal edges are not supplied by the M6 response.
 */
export function projectComparisonCausalTrace(
  response: ShadowTrialResponse,
  options: ProjectComparisonTraceOptions = {},
): ComparisonCausalTrace {
  const trialId = requiredId(response.id, "trial id");
  const baselineEnsembleId = requiredId(response.baseline_ensemble_id, "baseline_ensemble_id");
  const scenarioId = requiredId(response.definition_id, "definition_id");
  const trialDefinition = response.definition;
  const definition = trialDefinition?.scenario;
  const provenance = canonicalRecord(response.provenance);
  const provenanceOrigin = provenance.origin_snapshot_id;
  const definitionOrigin = definition?.origin_snapshot_id ?? null;
  const originSnapshotId = typeof provenanceOrigin === "string"
    ? requiredId(provenanceOrigin, "provenance origin_snapshot_id")
    : definitionOrigin;

  if (definitionOrigin !== null && originSnapshotId !== null && definitionOrigin !== originSnapshotId) {
    throw new RangeError("M6 scenario origin_snapshot_id does not match provenance origin_snapshot_id");
  }
  if (trialDefinition && trialDefinition.id !== scenarioId) {
    throw new RangeError("M6 definition_id does not match definition.id");
  }
  if (trialDefinition && trialDefinition.baseline_ensemble_id !== baselineEnsembleId) {
    throw new RangeError("M6 baseline_ensemble_id does not match definition baseline_ensemble_id");
  }
  if (definition && definition.id !== scenarioId) {
    throw new RangeError("M6 definition_id does not match scenario.id");
  }

  const pairs = selectedPairs(response, options);
  const evidenceIds = typeof provenance.evidence_ids === "object" && Array.isArray(provenance.evidence_ids)
    ? uniqueSorted(provenance.evidence_ids.filter((value): value is string => typeof value === "string"))
    : EMPTY_EVIDENCE;
  const pairingPolicy = typeof provenance.pairing_policy === "string"
    ? provenance.pairing_policy
    : null;
  const scenarioParameterChanges = scenarioParameters(response);
  const steps: ComparisonTraceStep[] = [];
  const originStepId = originSnapshotId === null ? undefined : `origin:${originSnapshotId}`;
  const originParents: readonly string[] = originStepId ? [originStepId] : [];
  const ensembleStepId = `ensemble:${baselineEnsembleId}`;
  const scenarioStepId = `scenario:${scenarioId}`;

  if (originStepId !== undefined && originSnapshotId !== null) {
    steps.push(step({
      id: originStepId,
      kind: "origin_snapshot",
      label: `Origin snapshot ${originSnapshotId}`,
      parentIds: [],
      evidenceIds,
      lineage: { originSnapshotId },
      details: {
        quality: provenance.origin_quality ?? null,
        originProvenance: provenance.origin_provenance ?? null,
      },
    }));
  }

  steps.push(step({
    id: ensembleStepId,
    kind: "baseline_ensemble",
    label: `Baseline ensemble ${baselineEnsembleId}`,
    parentIds: originParents,
    evidenceIds,
    lineage: {
      ...(originSnapshotId === null ? {} : { originSnapshotId }),
      baselineEnsembleId,
    },
    details: {
      seed: provenance.seed ?? null,
      physiologyVersion: provenance.physiology_version ?? null,
      ensembleVersion: provenance.ensemble_version ?? null,
      priorVersion: provenance.prior_version ?? null,
    },
  }));

  steps.push(step({
    id: scenarioStepId,
    kind: "scenario_definition",
    label: `Scenario ${scenarioId}`,
    parentIds: originParents,
    evidenceIds: [],
    lineage: {
      ...(originSnapshotId === null ? {} : { originSnapshotId }),
      scenarioId,
    },
    details: {
      label: definition?.label ?? null,
      description: definition?.description ?? null,
      createdAt: definition?.created_at ?? null,
      parameters: scenarioParameterChanges.map((parameter) => canonicalValue(parameter)),
      definitionHash: provenance.scenario_definition_hash ?? null,
    },
  }));

  const pairLineages: ComparisonPairLineage[] = [];
  for (const pair of pairs) {
    pairLineages.push(pairLineage(pair));
    const baselineStepId = `baseline-twin:${pair.baseline_twin_id}`;
    const scenarioTwinStepId = `scenario-twin:${pair.scenario_twin_id}`;
    const pairStepId = `pair:${pair.sample_id}`;
    const pairEvidenceIds: readonly string[] = [];

    steps.push(step({
      id: baselineStepId,
      kind: "baseline_twin",
      label: `Baseline twin ${pair.baseline_twin_id}`,
      parentIds: [ensembleStepId],
      evidenceIds: pairEvidenceIds,
      lineage: {
        baselineEnsembleId,
        sampleId: pair.sample_id,
        baselineTwinId: pair.baseline_twin_id,
      },
      details: { parameters: parameterRecord(pair.baseline_parameters) },
    }));

    steps.push(step({
      id: scenarioTwinStepId,
      kind: "scenario_twin",
      label: `Scenario twin ${pair.scenario_twin_id}`,
      parentIds: [baselineStepId, scenarioStepId],
      evidenceIds: pairEvidenceIds,
      lineage: {
        scenarioId,
        sampleId: pair.sample_id,
        baselineTwinId: pair.baseline_twin_id,
        scenarioTwinId: pair.scenario_twin_id,
      },
      details: {
        parameters: parameterRecord(pair.scenario_parameters),
        application: pairingPolicy,
      },
    }));

    steps.push(step({
      id: pairStepId,
      kind: "paired_comparison",
      label: `Paired comparison ${pair.sample_id}`,
      parentIds: [baselineStepId, scenarioTwinStepId],
      evidenceIds: pairEvidenceIds,
      lineage: {
        sampleId: pair.sample_id,
        baselineTwinId: pair.baseline_twin_id,
        scenarioTwinId: pair.scenario_twin_id,
      },
      details: {
        valid: pair.valid,
        rejectionReasons: [...pair.rejection_reasons],
        parameters: parameterRecord(pair.parameters),
      },
    }));

    for (const metricId of Object.keys(pair.deltas).sort(compareStrings)) {
      const delta = pair.deltas[metricId as keyof typeof pair.deltas];
      if (typeof delta !== "number" || !Number.isFinite(delta)) {
        throw new RangeError(`M6 pair ${pair.sample_id} has a non-finite delta for ${metricId}`);
      }
      steps.push(step({
        id: `delta:${pair.sample_id}:${metricId}`,
        kind: "paired_delta",
        label: `Paired delta ${metricId}`,
        parentIds: [pairStepId],
        evidenceIds: pairEvidenceIds,
        lineage: { sampleId: pair.sample_id },
        details: {
          metricId,
          delta,
          unit: pair.delta_units[metricId] ?? null,
        },
      }));
    }
  }

  const trace: ComparisonCausalTrace = {
    id: `comparison-trace:${trialId}`,
    trialId,
    status: response.status,
    deterministic: true,
    originSnapshotId,
    baselineEnsembleId,
    scenarioId,
    pairIds: pairs.map((pair) => pair.sample_id),
    evidenceIds,
    provenance,
    lineage: {
      originSnapshotId,
      baselineEnsembleId,
      scenarioId,
      pairingPolicy,
      pairs: pairLineages,
    },
    steps,
    warnings: uniqueSorted(response.warnings),
    safetyDisclaimer: response.safety_disclaimer,
  };

  return freezeDeep(trace);
}

/** Explicit alias for callers that name the operation as a builder. */
export const buildComparisonCausalTrace = projectComparisonCausalTrace;

/** Project one retained pair without changing the full-trial contract. */
export function projectPairCausalTrace(
  response: ShadowTrialResponse,
  pairId: string,
): ComparisonCausalTrace {
  return projectComparisonCausalTrace(response, { pairId });
}
