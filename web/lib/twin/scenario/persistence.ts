import type {
  ObservedOriginMetadata,
  ScenarioDefinition,
  ScenarioResult,
  ScenarioTwinState,
} from "@/lib/twin/scenario/types";

/** The on-disk format version for persisted scenario data. */
export const SCENARIO_PERSISTENCE_VERSION = 1 as const;

export type ScenarioPersistenceKind = "definition" | "result";

export interface ScenarioDefinitionEnvelope {
  readonly version: typeof SCENARIO_PERSISTENCE_VERSION;
  readonly kind: "definition";
  readonly payload: ScenarioDefinition;
}

export interface ScenarioResultEnvelope {
  readonly version: typeof SCENARIO_PERSISTENCE_VERSION;
  readonly kind: "result";
  readonly payload: ScenarioResult;
}

export type ScenarioPersistenceEnvelope =
  | ScenarioDefinitionEnvelope
  | ScenarioResultEnvelope;

export class ScenarioPersistenceError extends Error {
  readonly field: string;

  constructor(field: string, message: string) {
    super(`Invalid scenario ${field}: ${message}`);
    this.name = "ScenarioPersistenceError";
    this.field = field;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/** Reject values that JSON.stringify would silently change or omit. */
function assertJsonSafe(
  value: unknown,
  field: string,
  seen = new WeakSet<object>(),
): void {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return;
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new ScenarioPersistenceError(field, "must contain only finite numbers");
    }
    return;
  }

  if (typeof value !== "object") {
    throw new ScenarioPersistenceError(field, "must contain only JSON-compatible values");
  }

  if (seen.has(value)) {
    throw new ScenarioPersistenceError(field, "must not contain circular references");
  }

  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null && !Array.isArray(value)) {
    throw new ScenarioPersistenceError(field, "must contain only plain JSON objects");
  }

  seen.add(value);
  if (Array.isArray(value)) {
    value.forEach((entry, index) => assertJsonSafe(entry, `${field}[${index}]`, seen));
  } else {
    for (const [key, entry] of Object.entries(value)) {
      assertJsonSafe(entry, `${field}.${key}`, seen);
    }
  }
  seen.delete(value);
}

function assertNonEmptyString(value: unknown, field: string): asserts value is string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new ScenarioPersistenceError(field, "must be a non-empty string");
  }
}

function assertFiniteNumber(value: unknown, field: string): asserts value is number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ScenarioPersistenceError(field, "must be a finite number");
  }
}

function assertStringArray(value: unknown, field: string): asserts value is string[] {
  if (!Array.isArray(value)) {
    throw new ScenarioPersistenceError(field, "must be an array");
  }
  value.forEach((entry, index) => assertNonEmptyString(entry, `${field}[${index}]`));
}

function assertProvenanceArray(value: unknown, field: string): void {
  if (!Array.isArray(value)) {
    throw new ScenarioPersistenceError(field, "must be an array");
  }
  value.forEach((entry, index) => {
    if (!isRecord(entry)) {
      throw new ScenarioPersistenceError(`${field}[${index}]`, "must be an object");
    }
    assertNonEmptyString(entry.source, `${field}[${index}].source`);
    if (entry.sourceId !== undefined) {
      assertNonEmptyString(entry.sourceId, `${field}[${index}].sourceId`);
    }
    if (entry.method !== undefined) {
      assertNonEmptyString(entry.method, `${field}[${index}].method`);
    }
    if (entry.confidence !== undefined) {
      assertFiniteNumber(entry.confidence, `${field}[${index}].confidence`);
    }
    if (entry.evidenceIds !== undefined) {
      assertStringArray(entry.evidenceIds, `${field}[${index}].evidenceIds`);
    }
    if (entry.note !== undefined) {
      assertNonEmptyString(entry.note, `${field}[${index}].note`);
    }
  });
}

function assertOrigin(value: unknown, field: string): asserts value is ObservedOriginMetadata {
  if (!isRecord(value)) {
    throw new ScenarioPersistenceError(field, "must be an object");
  }
  assertNonEmptyString(value.snapshotId, `${field}.snapshotId`);
  assertNonEmptyString(value.patientId, `${field}.patientId`);
  assertNonEmptyString(value.timestamp, `${field}.timestamp`);
  if (!isRecord(value.state)) {
    throw new ScenarioPersistenceError(`${field}.state`, "must be an object");
  }
  assertProvenanceArray(value.provenance, `${field}.provenance`);
  assertStringArray(value.evidenceIds, `${field}.evidenceIds`);
}

function assertScenarioDefinition(
  value: unknown,
  field = "payload",
): asserts value is ScenarioDefinition {
  if (!isRecord(value)) {
    throw new ScenarioPersistenceError(field, "must be an object");
  }
  assertNonEmptyString(value.id, `${field}.id`);
  assertNonEmptyString(value.label, `${field}.label`);
  if (value.description !== undefined) {
    if (typeof value.description !== "string") {
      throw new ScenarioPersistenceError(`${field}.description`, "must be a string");
    }
  }
  assertOrigin(value.origin, `${field}.origin`);
  if (!Array.isArray(value.parameters)) {
    throw new ScenarioPersistenceError(`${field}.parameters`, "must be an array");
  }
  value.parameters.forEach((entry, index) => {
    const parameterField = `${field}.parameters[${index}]`;
    if (!isRecord(entry)) {
      throw new ScenarioPersistenceError(parameterField, "must be an object");
    }
    assertNonEmptyString(entry.parameter, `${parameterField}.parameter`);
    assertFiniteNumber(entry.baseline, `${parameterField}.baseline`);
    assertFiniteNumber(entry.value, `${parameterField}.value`);
    assertFiniteNumber(entry.delta, `${parameterField}.delta`);
    assertNonEmptyString(entry.unit, `${parameterField}.unit`);
  });
  assertNonEmptyString(value.createdAt, `${field}.createdAt`);
}

function assertScenarioTwinState(value: unknown, field: string): asserts value is ScenarioTwinState {
  if (!isRecord(value)) {
    throw new ScenarioPersistenceError(field, "must be an object");
  }
  assertNonEmptyString(value.scenarioId, `${field}.scenarioId`);
  assertOrigin(value.origin, `${field}.origin`);
  if (!isRecord(value.state)) {
    throw new ScenarioPersistenceError(`${field}.state`, "must be an object");
  }
  assertNonEmptyString(value.timestamp, `${field}.timestamp`);
  assertProvenanceArray(value.provenance, `${field}.provenance`);
}

function assertScenarioResult(value: unknown, field = "payload"): asserts value is ScenarioResult {
  if (!isRecord(value)) {
    throw new ScenarioPersistenceError(field, "must be an object");
  }
  assertScenarioDefinition(value.definition, `${field}.definition`);
  assertOrigin(value.baseline, `${field}.baseline`);
  assertScenarioTwinState(value.scenario, `${field}.scenario`);
  if (!Array.isArray(value.componentDeltas)) {
    throw new ScenarioPersistenceError(`${field}.componentDeltas`, "must be an array");
  }
  value.componentDeltas.forEach((entry, index) => {
    const deltaField = `${field}.componentDeltas[${index}]`;
    if (!isRecord(entry)) {
      throw new ScenarioPersistenceError(deltaField, "must be an object");
    }
    assertNonEmptyString(entry.componentId, `${deltaField}.componentId`);
    assertNonEmptyString(entry.metric, `${deltaField}.metric`);
    for (const key of ["baseline", "scenario", "delta"] as const) {
      if (entry[key] !== null) {
        assertFiniteNumber(entry[key], `${deltaField}.${key}`);
      }
    }
    if (entry.componentCategory !== undefined) {
      assertNonEmptyString(entry.componentCategory, `${deltaField}.componentCategory`);
    }
    if (entry.unit !== undefined) {
      assertNonEmptyString(entry.unit, `${deltaField}.unit`);
    }
    if (entry.direction !== "increase" && entry.direction !== "decrease" && entry.direction !== "unchanged") {
      throw new ScenarioPersistenceError(`${deltaField}.direction`, "must be a valid delta direction");
    }
    assertProvenanceArray(entry.provenance, `${deltaField}.provenance`);
  });
  assertProvenanceArray(value.provenance, `${field}.provenance`);
  if (value.status !== "draft" && value.status !== "computed" && value.status !== "failed") {
    throw new ScenarioPersistenceError(`${field}.status`, "must be a valid scenario status");
  }
  assertStringArray(value.warnings, `${field}.warnings`);
  assertNonEmptyString(value.computedAt, `${field}.computedAt`);
}

function envelopeFor<T extends ScenarioPersistenceEnvelope>(envelope: T): string {
  assertJsonSafe(envelope, "envelope");
  return JSON.stringify(envelope);
}

function parseEnvelope(
  input: string | unknown,
  expectedKind: ScenarioPersistenceKind,
): Record<string, unknown> {
  let parsed: unknown = input;
  if (typeof input === "string") {
    try {
      parsed = JSON.parse(input) as unknown;
    } catch {
      throw new ScenarioPersistenceError("serialized", "must contain valid JSON");
    }
  }

  if (!isRecord(parsed)) {
    throw new ScenarioPersistenceError("serialized", "must contain an object envelope");
  }
  assertJsonSafe(parsed, "serialized");
  if (parsed.version !== SCENARIO_PERSISTENCE_VERSION || parsed.kind !== expectedKind) {
    throw new ScenarioPersistenceError(
      "serialized",
      `must be a version ${SCENARIO_PERSISTENCE_VERSION} ${expectedKind} envelope`,
    );
  }
  if (!Object.prototype.hasOwnProperty.call(parsed, "payload")) {
    throw new ScenarioPersistenceError("serialized.payload", "is required");
  }
  return parsed;
}

/** Serialize a scenario definition into a versioned local-storage-safe string. */
export function serializeScenarioDefinition(definition: ScenarioDefinition): string {
  assertScenarioDefinition(definition);
  return envelopeFor({
    version: SCENARIO_PERSISTENCE_VERSION,
    kind: "definition",
    payload: definition,
  });
}

/** Deserialize and validate a persisted scenario definition. */
export function deserializeScenarioDefinition(
  input: string | unknown,
): ScenarioDefinition {
  const envelope = parseEnvelope(input, "definition");
  assertScenarioDefinition(envelope.payload);
  return JSON.parse(JSON.stringify(envelope.payload)) as ScenarioDefinition;
}

/** Serialize a computed scenario result into a versioned local-storage-safe string. */
export function serializeScenarioResult(result: ScenarioResult): string {
  assertScenarioResult(result);
  return envelopeFor({
    version: SCENARIO_PERSISTENCE_VERSION,
    kind: "result",
    payload: result,
  });
}

/** Deserialize and validate a persisted scenario result. */
export function deserializeScenarioResult(input: string | unknown): ScenarioResult {
  const envelope = parseEnvelope(input, "result");
  assertScenarioResult(envelope.payload);
  return JSON.parse(JSON.stringify(envelope.payload)) as ScenarioResult;
}
