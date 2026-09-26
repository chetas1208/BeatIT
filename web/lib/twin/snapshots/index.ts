import type {
  CardiacTwinState,
  SimulationVisualization,
} from "@/types/heart";
import type {
  SnapshotQuality,
  StateChangeReason,
  TwinEvent,
  TwinProvenance,
  TwinSnapshot,
  TwinStateChange,
  TwinTimeline,
  TwinTimestamp,
} from "@/lib/twin/time/contracts";
import { compareTwinEvents } from "@/lib/twin/time/contracts";
import { reduceTwinEvent } from "@/lib/twin/reducer";

/**
 * The snapshot engine deliberately accepts a reducer instead of importing one.
 * This keeps reconstruction pure and lets the domain reducer evolve without a
 * circular dependency between the two modules.
 */
export interface SnapshotReduction {
  state: CardiacTwinState;
  changes?: readonly TwinStateChange[];
  evidenceIds?: readonly string[];
  provenance?: readonly TwinProvenance[];
  quality?: SnapshotQuality;
  visualization?: SimulationVisualization;
}

export interface SnapshotReducerContext {
  eventIndex: number;
  orderedEvents: readonly TwinEvent[];
  previousSnapshot: TwinSnapshot | null;
}

export type SnapshotReducerResult = CardiacTwinState | SnapshotReduction;

export type SnapshotReducer = (
  state: CardiacTwinState,
  event: TwinEvent,
  context: SnapshotReducerContext,
) => SnapshotReducerResult;

export interface SnapshotTimelineOptions {
  patientId?: string;
  /** Defaults to sorting by timestamp and then event ID. */
  sortEvents?: boolean;
  initialTimestamp?: TwinTimestamp;
  initialQuality?: SnapshotQuality;
  initialEvidenceIds?: readonly string[];
  initialProvenance?: readonly TwinProvenance[];
  initialVisualization?: SimulationVisualization;
  reducer?: SnapshotReducer;
}

export interface SnapshotInput {
  id: string;
  timestamp: TwinTimestamp;
  state: CardiacTwinState;
  visualization?: SimulationVisualization;
  evidenceIds?: readonly string[];
  changedFields?: readonly TwinStateChange[];
  provenance?: readonly TwinProvenance[];
  quality?: SnapshotQuality;
}

function cloneValue<T>(value: T): T {
  if (value === null || typeof value !== "object") {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map((item) => cloneValue(item)) as T;
  }

  const cloned: Record<string, unknown> = {};
  for (const [key, nestedValue] of Object.entries(value as Record<string, unknown>)) {
    cloned[key] = cloneValue(nestedValue);
  }
  return cloned as T;
}

function freezeDeep<T>(value: T, seen = new WeakSet<object>()): T {
  if (value === null || typeof value !== "object") {
    return value;
  }

  if (seen.has(value)) {
    return value;
  }
  seen.add(value);

  for (const nestedValue of Object.values(value as Record<string, unknown>)) {
    freezeDeep(nestedValue, seen);
  }
  return Object.freeze(value);
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value) ?? String(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }

  const record = value as Record<string, unknown>;
  return `{${Object.keys(record)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stableStringify(record[key])}`)
    .join(",")}}`;
}

function stableHash(value: string): string {
  // FNV-1a is small, deterministic, and available in every supported runtime.
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function uniqueStrings(values: readonly string[]): string[] {
  return [...new Set(values.filter((value) => value.length > 0))];
}

function provenanceKey(provenance: TwinProvenance): string {
  return stableStringify(provenance);
}

function uniqueProvenance(values: readonly TwinProvenance[]): TwinProvenance[] {
  const seen = new Set<string>();
  const result: TwinProvenance[] = [];
  for (const item of values) {
    const key = provenanceKey(item);
    if (!seen.has(key)) {
      seen.add(key);
      result.push(cloneValue(item));
    }
  }
  return result;
}

function valuesEqual(left: unknown, right: unknown): boolean {
  return stableStringify(left) === stableStringify(right);
}

function getPayloadRecord(event: TwinEvent): Record<string, unknown> | null {
  if (!event.payload || typeof event.payload !== "object" || Array.isArray(event.payload)) {
    return null;
  }
  return event.payload as Record<string, unknown>;
}

function eventQuality(event: TwinEvent): SnapshotQuality {
  if (event.source === "synthetic_replay") {
    return "synthetic";
  }
  if (event.type === "state_update") {
    return "derived";
  }
  return "observed";
}

function eventReason(event: TwinEvent): StateChangeReason {
  if (event.type === "state_update") {
    return "deterministic_derivation";
  }
  return "new_evidence";
}

function payloadVisualization(event: TwinEvent): SimulationVisualization | undefined {
  const payload = getPayloadRecord(event);
  if (!payload || !("visualization" in payload)) {
    return undefined;
  }
  return payload.visualization as SimulationVisualization | undefined;
}

function payloadProvenance(event: TwinEvent): TwinProvenance[] {
  const payload = getPayloadRecord(event);
  const provenance = payload?.provenance;
  return provenance && typeof provenance === "object" && !Array.isArray(provenance)
    ? [provenance as TwinProvenance]
    : [];
}

function payloadEvidenceIds(event: TwinEvent): string[] {
  const payload = getPayloadRecord(event);
  const evidenceIds = payload?.evidenceIds;
  return Array.isArray(evidenceIds)
    ? evidenceIds.filter((value): value is string => typeof value === "string")
    : [];
}

function diffValues(
  previousValue: unknown,
  nextValue: unknown,
  path: string,
  reason: StateChangeReason,
  evidenceIds: readonly string[],
): TwinStateChange[] {
  if (valuesEqual(previousValue, nextValue)) {
    return [];
  }

  if (
    previousValue &&
    nextValue &&
    typeof previousValue === "object" &&
    typeof nextValue === "object" &&
    !Array.isArray(previousValue) &&
    !Array.isArray(nextValue)
  ) {
    const keys = new Set([
      ...Object.keys(previousValue as Record<string, unknown>),
      ...Object.keys(nextValue as Record<string, unknown>),
    ]);
    return [...keys]
      .sort()
      .flatMap((key) =>
        diffValues(
          (previousValue as Record<string, unknown>)[key],
          (nextValue as Record<string, unknown>)[key],
          path ? `${path}.${key}` : key,
          reason,
          evidenceIds,
        ),
      );
  }

  return [
    {
      path,
      previousValue: cloneValue(previousValue),
      nextValue: cloneValue(nextValue),
      reason,
      evidenceIds: [...evidenceIds],
    },
  ];
}

function defaultReduce(
  state: CardiacTwinState,
  event: TwinEvent,
): SnapshotReduction {
  const payload = getPayloadRecord(event);
  const evidenceIds = uniqueStrings([
    event.id,
    ...(event.provenance.evidenceIds ?? []),
    ...payloadEvidenceIds(event),
  ]);
  const reason = eventReason(event);

  // The canonical reducer owns CardiacTwinState path validation and wearable
  // handling. Keep the full-state form as a small compatibility escape hatch
  // for serialized replay fixtures that already contain a complete state.
  const fullState = payload?.state ?? payload?.nextState;
  if (fullState && typeof fullState === "object" && !Array.isArray(fullState)) {
    const nextState = cloneValue(fullState) as CardiacTwinState;
    return {
      state: nextState,
      changes: diffValues(state, nextState, "", reason, evidenceIds),
      evidenceIds,
      quality: eventQuality(event),
    };
  }

  const reduction = reduceTwinEvent(state, event);
  return {
    state: reduction.state,
    changes: reduction.changes,
    evidenceIds,
    quality: eventQuality(event),
  };
}

function isSnapshotReduction(value: SnapshotReducerResult): value is SnapshotReduction {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    "state" in value &&
    typeof value.state === "object" &&
    value.state !== null
  );
}

function normalizeReduction(
  result: SnapshotReducerResult,
): SnapshotReduction {
  if (isSnapshotReduction(result)) {
    return result;
  }
  return { state: result as CardiacTwinState };
}

function sortEvents(events: readonly TwinEvent[]): TwinEvent[] {
  const seenIds = new Set<string>();
  return events
    .slice()
    .sort(compareTwinEvents)
    .filter((event) => {
      if (seenIds.has(event.id)) return false;
      seenIds.add(event.id);
      return true;
    });
}

function snapshotId(
  patientId: string,
  timestamp: TwinTimestamp,
  eventId: string,
  occurrence: number,
): string {
  return `snapshot-${stableHash(stableStringify([patientId, timestamp, eventId, occurrence]))}`;
}

function freezeSnapshot(input: SnapshotInput): TwinSnapshot {
  const snapshot = {
    id: input.id,
    timestamp: input.timestamp,
    state: cloneValue(input.state),
    ...(input.visualization === undefined ? {} : { visualization: cloneValue(input.visualization) }),
    evidenceIds: uniqueStrings(input.evidenceIds ?? []),
    changedFields: cloneValue(input.changedFields ?? []) as TwinStateChange[],
    provenance: uniqueProvenance(input.provenance ?? []),
    quality: input.quality ?? "observed",
  } satisfies TwinSnapshot;
  return freezeDeep(snapshot);
}

/** Build one deeply immutable snapshot from already-reduced values. */
export function buildSnapshot(input: SnapshotInput): TwinSnapshot {
  return freezeSnapshot(input);
}

/** Alias that makes call sites explicit when building a timeline entry. */
export const createTwinSnapshot = buildSnapshot;

/**
 * Reconstruct a deterministic timeline from a baseline state and events.
 * Events are sorted by timestamp and stable ID by default; callers that have
 * already applied an ordering policy can opt out with `sortEvents: false`.
 */
export function reconstructTimeline(
  initialState: CardiacTwinState,
  events: readonly TwinEvent[],
  options: SnapshotTimelineOptions = {},
): TwinTimeline {
  const patientId = options.patientId ?? initialState.case_id;
  const orderedEvents = options.sortEvents === false ? dedupeEvents(events) : sortEvents(events);
  const initialTimestamp = options.initialTimestamp ?? initialState.created_at;
  const snapshots: TwinSnapshot[] = [
    freezeSnapshot({
      id: snapshotId(patientId, initialTimestamp, "initial", 0),
      timestamp: initialTimestamp,
      state: initialState,
      visualization: options.initialVisualization,
      evidenceIds: options.initialEvidenceIds,
      provenance: options.initialProvenance,
      quality: options.initialQuality ?? "observed",
      changedFields: [],
    }),
  ];

  let state = cloneValue(initialState);
  let previousSnapshot = snapshots[0];
  const eventOccurrences = new Map<string, number>();

  orderedEvents.forEach((event, eventIndex) => {
    const occurrence = eventOccurrences.get(event.id) ?? 0;
    eventOccurrences.set(event.id, occurrence + 1);
    const reduction = normalizeReduction(
      (options.reducer ?? defaultReduce)(state, event, {
        eventIndex,
        orderedEvents,
        previousSnapshot,
      }),
    );
    const payload = getPayloadRecord(event);
    const changes = reduction.changes
      ? cloneValue(reduction.changes)
      : [];
    const evidenceIds = uniqueStrings([
      ...(previousSnapshot?.evidenceIds ?? []),
      event.id,
      ...(event.provenance.evidenceIds ?? []),
      ...payloadEvidenceIds(event),
      ...(reduction.evidenceIds ?? []),
      ...changes.flatMap((change) => change.evidenceIds),
    ]);
    const provenance = uniqueProvenance([
      ...(previousSnapshot?.provenance ?? []),
      event.provenance,
      ...payloadProvenance(event),
      ...(reduction.provenance ?? []),
    ]);
    const hasReductionVisualization = Object.prototype.hasOwnProperty.call(reduction, "visualization");
    const visualization = hasReductionVisualization
      ? reduction.visualization
      : payload && Object.prototype.hasOwnProperty.call(payload, "visualization")
        ? payloadVisualization(event)
        : previousSnapshot?.visualization;
    const quality = reduction.quality ?? (
      event.type === "annotation" || changes.length === 0
        ? previousSnapshot.quality
        : eventQuality(event)
    );
    const snapshot = freezeSnapshot({
      id: snapshotId(patientId, event.timestamp, event.id, occurrence),
      timestamp: event.timestamp,
      state: reduction.state,
      ...(visualization === undefined ? {} : { visualization }),
      evidenceIds,
      changedFields: changes,
      provenance,
      quality,
    });
    snapshots.push(snapshot);
    state = cloneValue(reduction.state);
    previousSnapshot = snapshot;
  });

  const immutableSnapshots = Object.freeze(snapshots.slice()) as readonly TwinSnapshot[];
  return Object.freeze({
    patientId,
    snapshots: immutableSnapshots,
    startTime: immutableSnapshots[0]!.timestamp,
    endTime: immutableSnapshots[immutableSnapshots.length - 1]!.timestamp,
    currentSnapshotId: immutableSnapshots[immutableSnapshots.length - 1]!.id,
  });
}

function dedupeEvents(events: readonly TwinEvent[]): TwinEvent[] {
  const seenIds = new Set<string>();
  return events.filter((event) => {
    if (seenIds.has(event.id)) return false;
    seenIds.add(event.id);
    return true;
  });
}

/** More descriptive alias for consumers that use the domain name. */
export const reconstructTwinTimeline = reconstructTimeline;

/** Return a detached copy when a consumer needs to serialize or edit a snapshot. */
export function cloneSnapshot(snapshot: TwinSnapshot): TwinSnapshot {
  return freezeSnapshot({
    id: snapshot.id,
    timestamp: snapshot.timestamp,
    state: snapshot.state,
    visualization: snapshot.visualization,
    evidenceIds: snapshot.evidenceIds,
    changedFields: snapshot.changedFields,
    provenance: snapshot.provenance,
    quality: snapshot.quality,
  });
}
