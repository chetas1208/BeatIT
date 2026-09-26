import {
  isTwinTimestamp,
  normalizeTwinEvent,
  type TwinEvent,
  type TwinEventSource,
  type TwinEventType,
  type TwinProvenance,
  compareTwinEvents,
} from "@/lib/twin/time/contracts";

const SERIALIZATION_VERSION = 1 as const;

const EVENT_TYPES: readonly TwinEventType[] = [
  "measurement",
  "clinical_evidence",
  "wearable_sample",
  "state_update",
  "annotation",
];

const EVENT_SOURCES: readonly TwinEventSource[] = [
  "clinical_record",
  "imaging",
  "ecg",
  "wearable",
  "synthetic_replay",
  "user_annotation",
  "derived_model",
];

export interface TwinCorrectionPayload {
  path: string;
  value: unknown;
  correctionOf: string;
  correctionReason?: string;
}

export interface TwinCorrectionInput {
  id: string;
  timestamp: string;
  source: TwinEventSource;
  correctionOf: string;
  path: string;
  value: unknown;
  provenance?: Omit<TwinProvenance, "source"> & { source?: TwinEventSource };
  correctionReason?: string;
}

export interface TwinEventStoreExport {
  version: typeof SERIALIZATION_VERSION;
  events: TwinEvent[];
}

export type TwinEventAppendStatus = "appended" | "duplicate";

export interface TwinEventAppendResult {
  status: TwinEventAppendStatus;
  event: Readonly<TwinEvent>;
  orderedIndex: number;
}

export class TwinEventValidationError extends Error {
  readonly field: string;

  constructor(field: string, message: string) {
    super(`Invalid twin event ${field}: ${message}`);
    this.name = "TwinEventValidationError";
    this.field = field;
  }
}

/**
 * Makes a JSON-compatible value immutable without exposing a mutable alias.
 * Event data is deliberately JSON-only so it can be persisted and replayed
 * consistently in the browser, server, and test runner.
 */
function cloneAndFreeze<T>(value: T, field: string): T {
  assertJsonValue(value, field);
  const clone = JSON.parse(JSON.stringify(value)) as T;
  return deepFreeze(clone);
}

function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const child of Object.values(value as Record<string, unknown>)) {
      deepFreeze(child);
    }
  }
  return value;
}

function assertJsonValue(value: unknown, field: string, seen = new WeakSet<object>()): void {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new TwinEventValidationError(field, "must contain only finite numbers");
    }
    return;
  }
  if (typeof value !== "object") {
    throw new TwinEventValidationError(field, "must be JSON-compatible");
  }
  if (seen.has(value)) {
    throw new TwinEventValidationError(field, "must not contain circular references");
  }
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null && !Array.isArray(value)) {
    throw new TwinEventValidationError(field, "must contain only plain JSON objects");
  }
  seen.add(value);
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertJsonValue(item, `${field}[${index}]`, seen));
  } else {
    for (const [key, child] of Object.entries(value)) {
      assertJsonValue(child, `${field}.${key}`, seen);
    }
  }
  seen.delete(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function assertNonEmptyString(value: unknown, field: string): asserts value is string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new TwinEventValidationError(field, "must be a non-empty string");
  }
}

function assertEnum<T extends string>(value: unknown, values: readonly T[], field: string): asserts value is T {
  if (typeof value !== "string" || !values.includes(value as T)) {
    throw new TwinEventValidationError(field, `must be one of: ${values.join(", ")}`);
  }
}

function validateProvenance(value: unknown): asserts value is TwinProvenance {
  if (!isRecord(value)) {
    throw new TwinEventValidationError("provenance", "must be an object");
  }
  assertEnum(value.source, EVENT_SOURCES, "provenance.source");
  for (const field of ["sourceId", "method", "note"] as const) {
    if (value[field] !== undefined && typeof value[field] !== "string") {
      throw new TwinEventValidationError(`provenance.${field}`, "must be a string when provided");
    }
  }
  if (value.confidence !== undefined &&
      (typeof value.confidence !== "number" || !Number.isFinite(value.confidence) || value.confidence < 0 || value.confidence > 1)) {
    throw new TwinEventValidationError("provenance.confidence", "must be a finite number between 0 and 1");
  }
  if (value.evidenceIds !== undefined &&
      (!Array.isArray(value.evidenceIds) || value.evidenceIds.some((id) => typeof id !== "string" || id.trim().length === 0))) {
    throw new TwinEventValidationError("provenance.evidenceIds", "must contain only non-empty strings");
  }
  assertJsonValue(value, "provenance");
}

function validatePayload(value: unknown): void {
  try {
    assertJsonValue(value, "payload");
  } catch (error) {
    if (error instanceof TwinEventValidationError) {
      throw new TwinEventValidationError("payload", error.message.replace(/^Invalid twin event payload:\s*/, ""));
    }
    throw error;
  }
}

function validateEvent(event: TwinEvent): void {
  if (!isRecord(event)) {
    throw new TwinEventValidationError("event", "must be an object");
  }
  assertNonEmptyString(event.id, "id");
  if (!isTwinTimestamp(event.timestamp)) {
    throw new TwinEventValidationError("timestamp", "must be an ISO-8601 timestamp with an explicit timezone");
  }
  assertEnum(event.type, EVENT_TYPES, "type");
  assertEnum(event.source, EVENT_SOURCES, "source");
  validatePayload(event.payload);
  validateProvenance(event.provenance);
}

export function validateTwinEvent(event: TwinEvent): void {
  validateEvent(event);
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(",")}]`;
  }
  if (isRecord(value)) {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function sameEvent(a: TwinEvent, b: TwinEvent): boolean {
  return canonicalJson(a) === canonicalJson(b);
}

function correctionFromInput(input: TwinCorrectionInput, correctedEvent: TwinEvent): TwinEvent {
  const provenance: TwinProvenance = {
    ...(input.provenance ?? {}),
    source: input.provenance?.source ?? input.source,
    evidenceIds: [
      ...(input.provenance?.evidenceIds ?? []),
      ...(correctedEvent.provenance.evidenceIds ?? []),
    ].filter((id, index, ids) => ids.indexOf(id) === index),
  };
  return {
    id: input.id,
    timestamp: input.timestamp,
    type: "state_update",
    source: input.source,
    payload: {
      path: input.path,
      value: input.value,
      correctionOf: correctedEvent.id,
      ...(input.correctionReason ? { correctionReason: input.correctionReason } : {}),
    } satisfies TwinCorrectionPayload,
    provenance,
  };
}

/**
 * Append-only event log with deterministic timestamp ordering.
 *
 * Events with the same ID are idempotent only when their complete immutable
 * content matches. A conflicting reuse of an ID is rejected. Different IDs
 * remain distinct even when their payloads match, preserving evidence history.
 * Out-of-order arrivals are sorted by the shared timestamp/event-content
 * comparator, giving the same replay order regardless of arrival order.
 */
export class TwinEventStore {
  private readonly records: Array<{ event: Readonly<TwinEvent>; sequence: number }> = [];
  private nextSequence = 0;

  constructor(events: readonly TwinEvent[] = []) {
    for (const event of events) {
      this.append(event);
    }
  }

  get size(): number {
    return this.records.length;
  }

  append(input: TwinEvent): TwinEventAppendResult {
    validateEvent(input);
    const normalizedInput = normalizeTwinEvent(input);
    const existing = this.records.find(({ event }) => event.id === normalizedInput.id);
    if (existing) {
      if (!sameEvent(existing.event, normalizedInput)) {
        throw new TwinEventValidationError("id", `event ID '${normalizedInput.id}' is already used by different content`);
      }
      return {
        status: "duplicate",
        event: existing.event,
        orderedIndex: this.getEvents().indexOf(existing.event),
      };
    }

    const event = cloneAndFreeze(normalizedInput, "event") as Readonly<TwinEvent>;
    this.records.push({ event, sequence: this.nextSequence });
    this.nextSequence += 1;
    const ordered = this.getEvents();
    return { status: "appended", event, orderedIndex: ordered.indexOf(event) };
  }

  /** Alias useful to callers that use event-log terminology. */
  add(input: TwinEvent): TwinEventAppendResult {
    return this.append(input);
  }

  appendCorrection(input: TwinCorrectionInput): TwinEventAppendResult {
    assertNonEmptyString(input.id, "id");
    assertNonEmptyString(input.correctionOf, "correctionOf");
    assertNonEmptyString(input.path, "path");
    const correctedEvent = this.get(input.correctionOf);
    if (!correctedEvent) {
      throw new TwinEventValidationError("correctionOf", `event '${input.correctionOf}' does not exist`);
    }
    const event = correctionFromInput(input, correctedEvent);
    return this.append(event);
  }

  has(id: string): boolean {
    return this.records.some(({ event }) => event.id === id);
  }

  get(id: string): Readonly<TwinEvent> | undefined {
    return this.records.find(({ event }) => event.id === id)?.event;
  }

  getEvents(): readonly Readonly<TwinEvent>[] {
    return Object.freeze(
      [...this.records]
        .sort((a, b) => compareTwinEvents(a.event, b.event) || a.sequence - b.sequence)
        .map(({ event }) => event),
    );
  }

  toJSON(): TwinEventStoreExport {
    return {
      version: SERIALIZATION_VERSION,
      events: this.getEvents().map((event) => JSON.parse(JSON.stringify(event)) as TwinEvent),
    };
  }

  export(): TwinEventStoreExport {
    return this.toJSON();
  }

  serialize(): string {
    return JSON.stringify(this.toJSON());
  }

  static fromJSON(input: string | unknown): TwinEventStore {
    let parsed: unknown = input;
    if (typeof input === "string") {
      try {
        parsed = JSON.parse(input) as unknown;
      } catch {
        throw new TwinEventValidationError("serialized", "must contain valid JSON");
      }
    }
    if (!isRecord(parsed) || parsed.version !== SERIALIZATION_VERSION || !Array.isArray(parsed.events)) {
      throw new TwinEventValidationError("serialized", "must be a version 1 event store export");
    }
    return new TwinEventStore(parsed.events as TwinEvent[]);
  }

  static import(input: string | unknown): TwinEventStore {
    return TwinEventStore.fromJSON(input);
  }
}

export function isTwinCorrectionEvent(event: TwinEvent): event is TwinEvent & { payload: TwinCorrectionPayload } {
  return event.type === "state_update" &&
    isRecord(event.payload) &&
    typeof event.payload.correctionOf === "string" &&
    typeof event.payload.path === "string" &&
    Object.prototype.hasOwnProperty.call(event.payload, "value");
}
