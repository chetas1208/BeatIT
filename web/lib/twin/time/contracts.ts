import type {
  CardiacTwinState,
  SimulationVisualization,
} from "@/types/heart";

/** ISO-8601 timestamp normalized to UTC with millisecond precision. */
export type TwinTimestamp = string;

/** Values accepted at ingestion boundaries before normalization. */
export type TwinTimestampInput = TwinTimestamp | Date | number;

export type TwinEventType =
  | "measurement"
  | "clinical_evidence"
  | "wearable_sample"
  | "state_update"
  | "annotation";

export type TwinEventSource =
  | "clinical_record"
  | "imaging"
  | "ecg"
  | "wearable"
  | "synthetic_replay"
  | "user_annotation"
  | "derived_model";

export interface TwinProvenance {
  source: TwinEventSource;
  sourceId?: string;
  method?: string;
  confidence?: number;
  evidenceIds?: string[];
  note?: string;
}

export interface TwinMeasurementPayload {
  path: string;
  value: unknown;
  unit?: string;
  provenance?: TwinProvenance;
}

export interface TwinEvent {
  id: string;
  timestamp: TwinTimestamp;
  type: TwinEventType;
  source: TwinEventSource;
  payload: unknown;
  provenance: TwinProvenance;
}

export type StateChangeReason =
  | "new_evidence"
  | "deterministic_derivation"
  | "interpolation"
  | "initialization";

export interface TwinStateChange {
  path: string;
  previousValue: unknown;
  nextValue: unknown;
  reason: StateChangeReason;
  evidenceIds: string[];
}

export type SnapshotQuality = "observed" | "derived" | "interpolated" | "synthetic";

export interface TwinSnapshot {
  id: string;
  timestamp: TwinTimestamp;
  state: CardiacTwinState;
  visualization?: SimulationVisualization;
  evidenceIds: string[];
  changedFields: TwinStateChange[];
  provenance: TwinProvenance[];
  quality: SnapshotQuality;
}

export interface TwinTimeline {
  patientId: string;
  snapshots: readonly TwinSnapshot[];
  startTime: TwinTimestamp;
  endTime: TwinTimestamp;
  currentSnapshotId: string | null;
}

export type TwinPlaybackMode = "live" | "paused" | "playing" | "scrubbing";

/** Compatibility aliases for callers that name the playback primitive directly. */
export type PlaybackClockMode = TwinPlaybackMode;

export type TwinPlaybackRate = 0.5 | 1 | 2 | 5 | 10;

export interface TwinPlaybackState {
  mode: TwinPlaybackMode;
  cursorTime: TwinTimestamp;
  playbackRate: TwinPlaybackRate;
  selectedSnapshotId: string | null;
}

export type PlaybackClockState = TwinPlaybackState;

export interface TwinTimelineDelta {
  from: TwinTimestamp;
  to: TwinTimestamp;
  elapsedMs: number;
}

export interface TimelineClockState {
  startTime: TwinTimestamp;
  endTime: TwinTimestamp;
  cursorTime: TwinTimestamp;
}

export type TimelineClockListener = (state: TimelineClockState) => void;
export type PlaybackClockListener = (state: TwinPlaybackState) => void;

export const TWIN_PLAYBACK_RATES: readonly TwinPlaybackRate[] = [0.5, 1, 2, 5, 10];

const ISO_TIMESTAMP_PATTERN =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:?\d{2})$/i;

function assertValidOffset(timestamp: string): void {
  const match = /([+-])(\d{2}):?(\d{2})$/.exec(timestamp);
  if (!match) return;

  const hours = Number(match[2]);
  const minutes = Number(match[3]);
  if (hours > 23 || minutes > 59) {
    throw new RangeError(`Invalid timestamp timezone offset: ${timestamp}`);
  }
}

function parseTimestamp(input: TwinTimestampInput): number {
  if (input instanceof Date) {
    const milliseconds = input.getTime();
    if (!Number.isFinite(milliseconds)) throw new RangeError("Invalid Date timestamp");
    return milliseconds;
  }

  if (typeof input === "number") {
    if (!Number.isFinite(input)) throw new RangeError("Timestamp milliseconds must be finite");
    return input;
  }

  const value = input.trim();
  if (!ISO_TIMESTAMP_PATTERN.test(value)) {
    throw new RangeError(`Timestamp must be ISO-8601 with an explicit timezone: ${input}`);
  }
  assertValidOffset(value);

  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds)) throw new RangeError(`Invalid timestamp: ${input}`);
  return milliseconds;
}

/** Normalize any accepted timestamp input to a canonical UTC ISO string. */
export function normalizeTwinTimestamp(input: TwinTimestampInput): TwinTimestamp {
  return new Date(parseTimestamp(input)).toISOString();
}

export function isTwinTimestamp(value: string): boolean {
  try {
    normalizeTwinTimestamp(value);
    return true;
  } catch {
    return false;
  }
}

export function isNormalizedTwinTimestamp(value: string): boolean {
  return isTwinTimestamp(value) && normalizeTwinTimestamp(value) === value;
}

export function compareTwinTimestamps(a: TwinTimestamp, b: TwinTimestamp): number {
  return parseTimestamp(a) - parseTimestamp(b);
}

function compareStrings(a: string, b: string): number {
  if (a < b) return -1;
  if (a > b) return 1;
  return 0;
}

/**
 * Serialize JSON-like values with sorted object keys for deterministic ties.
 * Event payloads are data contracts, so cyclic values are rejected instead of
 * silently producing an order that depends on runtime object identity.
 */
function stableSerialize(value: unknown, seen = new Set<object>()): string {
  if (value === null) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number" || typeof value === "boolean") return JSON.stringify(value);
  if (typeof value === "bigint") return `bigint:${value.toString()}`;
  if (typeof value === "undefined") return "undefined";
  if (value instanceof Date) return `date:${normalizeTwinTimestamp(value)}`;
  if (typeof value !== "object") return `${typeof value}:${String(value)}`;
  if (seen.has(value)) throw new TypeError("Twin event payloads must not contain cycles");
  seen.add(value);

  if (Array.isArray(value)) {
    const serialized = `[${value.map((entry) => stableSerialize(entry, seen)).join(",")}]`;
    seen.delete(value);
    return serialized;
  }

  const objectValue = value as Record<string, unknown>;
  const serialized = `{${Object.keys(objectValue)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stableSerialize(objectValue[key], seen)}`)
    .join(",")}}`;
  seen.delete(value);
  return serialized;
}

/** Normalize one event without mutating the caller's event object. */
export function normalizeTwinEvent(event: TwinEvent): TwinEvent {
  return {
    ...event,
    timestamp: normalizeTwinTimestamp(event.timestamp),
    provenance: {
      ...event.provenance,
      evidenceIds: event.provenance.evidenceIds
        ? [...event.provenance.evidenceIds]
        : undefined,
    },
  };
}

/**
 * Compare events by timestamp and deterministic event content. For events
 * that are identical in every exposed field, `sortTwinEvents` preserves input
 * order as the final stable tie-breaker.
 */
export function compareTwinEvents(a: TwinEvent, b: TwinEvent): number {
  const timestampOrder = compareTwinTimestamps(a.timestamp, b.timestamp);
  if (timestampOrder !== 0) return timestampOrder;

  const idOrder = compareStrings(a.id, b.id);
  if (idOrder !== 0) return idOrder;
  const typeOrder = compareStrings(a.type, b.type);
  if (typeOrder !== 0) return typeOrder;
  const sourceOrder = compareStrings(a.source, b.source);
  if (sourceOrder !== 0) return sourceOrder;
  const payloadOrder = compareStrings(stableSerialize(a.payload), stableSerialize(b.payload));
  if (payloadOrder !== 0) return payloadOrder;
  return compareStrings(stableSerialize(a.provenance), stableSerialize(b.provenance));
}

/** Return normalized events in deterministic chronological order. */
export function sortTwinEvents(events: readonly TwinEvent[]): TwinEvent[] {
  return events
    .map((event, index) => ({ event: normalizeTwinEvent(event), index }))
    .sort((a, b) => compareTwinEvents(a.event, b.event) || a.index - b.index)
    .map(({ event }) => event);
}

function assertFiniteDelta(deltaMs: number): void {
  if (!Number.isFinite(deltaMs) || deltaMs < 0) {
    throw new RangeError("Clock delta must be a finite, non-negative number");
  }
}

function clampTimestamp(timestamp: TwinTimestamp, startTime: TwinTimestamp, endTime: TwinTimestamp): TwinTimestamp {
  if (compareTwinTimestamps(timestamp, startTime) < 0) return startTime;
  if (compareTwinTimestamps(timestamp, endTime) > 0) return endTime;
  return timestamp;
}

/**
 * History-time cursor. It has no wall-clock timer and never changes heart
 * rate or beat phase. Callers drive it with explicit milliseconds.
 */
export class TimelineClock {
  private state: TimelineClockState;
  private readonly listeners = new Set<TimelineClockListener>();

  constructor(startTime: TwinTimestampInput, endTime: TwinTimestampInput, cursorTime = startTime) {
    const start = normalizeTwinTimestamp(startTime);
    const end = normalizeTwinTimestamp(endTime);
    if (compareTwinTimestamps(start, end) > 0) {
      throw new RangeError("Timeline startTime must not be after endTime");
    }

    this.state = {
      startTime: start,
      endTime: end,
      cursorTime: clampTimestamp(normalizeTwinTimestamp(cursorTime), start, end),
    };
  }

  getState(): TimelineClockState {
    return { ...this.state };
  }

  setRange(startTime: TwinTimestampInput, endTime: TwinTimestampInput, cursorTime = this.state.cursorTime): void {
    const start = normalizeTwinTimestamp(startTime);
    const end = normalizeTwinTimestamp(endTime);
    if (compareTwinTimestamps(start, end) > 0) {
      throw new RangeError("Timeline startTime must not be after endTime");
    }
    this.state = {
      startTime: start,
      endTime: end,
      cursorTime: clampTimestamp(normalizeTwinTimestamp(cursorTime), start, end),
    };
    this.emit();
  }

  seek(cursorTime: TwinTimestampInput): TimelineClockState {
    const cursor = clampTimestamp(
      normalizeTwinTimestamp(cursorTime),
      this.state.startTime,
      this.state.endTime,
    );
    if (cursor !== this.state.cursorTime) {
      this.state = { ...this.state, cursorTime: cursor };
      this.emit();
    }
    return this.getState();
  }

  advance(deltaMs: number): TimelineClockState {
    assertFiniteDelta(deltaMs);
    if (deltaMs === 0 || this.isAtEnd()) return this.getState();
    const next = Date.parse(this.state.cursorTime) + deltaMs;
    return this.seek(next);
  }

  isAtStart(): boolean {
    return this.state.cursorTime === this.state.startTime;
  }

  isAtEnd(): boolean {
    return this.state.cursorTime === this.state.endTime;
  }

  subscribe(listener: TimelineClockListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(): void {
    const snapshot = this.getState();
    this.listeners.forEach((listener) => listener(snapshot));
  }
}

export interface PlaybackClockOptions {
  playbackRate?: TwinPlaybackRate;
  selectedSnapshotId?: string | null;
}

/**
 * Playback-time controller over a TimelineClock. `advance` receives an
 * explicit wall-time delta and applies playback rate; it never schedules a
 * timer. Scrubbing and playing are therefore deterministic and testable.
 */
export class PlaybackClock {
  private state: TwinPlaybackState;
  private readonly listeners = new Set<PlaybackClockListener>();
  private readonly timelineUnsubscribe: () => void;
  private applyingTimelineChange = false;

  constructor(
    private readonly timeline: TimelineClock,
    options: PlaybackClockOptions = {},
  ) {
    const playbackRate = options.playbackRate ?? 1;
    assertPlaybackRate(playbackRate);
    const timelineState = timeline.getState();
    this.state = {
      mode: timeline.isAtEnd() ? "live" : "paused",
      cursorTime: timelineState.cursorTime,
      playbackRate,
      selectedSnapshotId: options.selectedSnapshotId ?? null,
    };
    this.timelineUnsubscribe = timeline.subscribe((nextTimelineState) => {
      if (this.applyingTimelineChange) return;
      const atEnd = nextTimelineState.cursorTime === nextTimelineState.endTime;
      this.state = {
        ...this.state,
        cursorTime: nextTimelineState.cursorTime,
        mode: atEnd && this.state.mode === "playing" ? "live" : this.state.mode,
        selectedSnapshotId: atEnd ? null : this.state.selectedSnapshotId,
      };
      this.emit();
    });
  }

  dispose(): void {
    this.timelineUnsubscribe();
    this.listeners.clear();
  }

  getState(): TwinPlaybackState {
    return { ...this.state };
  }

  getTimeline(): TimelineClock {
    return this.timeline;
  }

  play(): TwinPlaybackState {
    if (!this.timeline.isAtEnd()) {
      this.state = { ...this.state, mode: "playing" };
      this.emit();
    }
    return this.getState();
  }

  pause(): TwinPlaybackState {
    this.state = {
      ...this.state,
      mode: this.timeline.isAtEnd() ? "live" : "paused",
    };
    this.emit();
    return this.getState();
  }

  beginScrubbing(): TwinPlaybackState {
    this.state = { ...this.state, mode: "scrubbing" };
    this.emit();
    return this.getState();
  }

  endScrubbing(): TwinPlaybackState {
    this.state = {
      ...this.state,
      mode: this.timeline.isAtEnd() ? "live" : "paused",
    };
    this.emit();
    return this.getState();
  }

  seek(cursorTime: TwinTimestampInput, selectedSnapshotId: string | null = null): TwinPlaybackState {
    this.withTimelineChange(() => this.timeline.seek(cursorTime));
    const atEnd = this.timeline.isAtEnd();
    this.state = {
      ...this.state,
      cursorTime: this.timeline.getState().cursorTime,
      mode: atEnd ? "live" : "paused",
      selectedSnapshotId: atEnd ? null : selectedSnapshotId,
    };
    this.emit();
    return this.getState();
  }

  scrubTo(cursorTime: TwinTimestampInput, selectedSnapshotId: string | null = null): TwinPlaybackState {
    this.withTimelineChange(() => this.timeline.seek(cursorTime));
    this.state = {
      ...this.state,
      mode: "scrubbing",
      cursorTime: this.timeline.getState().cursorTime,
      selectedSnapshotId: this.timeline.isAtEnd() ? null : selectedSnapshotId,
    };
    this.emit();
    return this.getState();
  }

  selectSnapshot(snapshotId: string | null): TwinPlaybackState {
    this.state = { ...this.state, selectedSnapshotId: snapshotId };
    this.emit();
    return this.getState();
  }

  setPlaybackRate(playbackRate: TwinPlaybackRate): TwinPlaybackState {
    assertPlaybackRate(playbackRate);
    if (playbackRate !== this.state.playbackRate) {
      this.state = { ...this.state, playbackRate };
      this.emit();
    }
    return this.getState();
  }

  jumpToLive(): TwinPlaybackState {
    this.withTimelineChange(() => this.timeline.seek(this.timeline.getState().endTime));
    this.state = {
      ...this.state,
      mode: "live",
      cursorTime: this.timeline.getState().cursorTime,
      selectedSnapshotId: null,
    };
    this.emit();
    return this.getState();
  }

  advance(realDeltaMs: number): TwinPlaybackState {
    assertFiniteDelta(realDeltaMs);
    if (this.state.mode !== "playing" || realDeltaMs === 0) return this.getState();

    this.withTimelineChange(() => this.timeline.advance(realDeltaMs * this.state.playbackRate));
    const atEnd = this.timeline.isAtEnd();
    this.state = {
      ...this.state,
      cursorTime: this.timeline.getState().cursorTime,
      mode: atEnd ? "live" : "playing",
      selectedSnapshotId: atEnd ? null : this.state.selectedSnapshotId,
    };
    this.emit();
    return this.getState();
  }

  subscribe(listener: PlaybackClockListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private withTimelineChange(operation: () => void): void {
    this.applyingTimelineChange = true;
    try {
      operation();
    } finally {
      this.applyingTimelineChange = false;
    }
  }

  private emit(): void {
    const snapshot = this.getState();
    this.listeners.forEach((listener) => listener(snapshot));
  }
}

function assertPlaybackRate(value: number): asserts value is TwinPlaybackRate {
  if (!TWIN_PLAYBACK_RATES.includes(value as TwinPlaybackRate)) {
    throw new RangeError(`Unsupported playback rate: ${value}`);
  }
}

export function createTimelineClock(
  startTime: TwinTimestampInput,
  endTime: TwinTimestampInput,
  cursorTime?: TwinTimestampInput,
): TimelineClock {
  return new TimelineClock(startTime, endTime, cursorTime ?? startTime);
}

export function createPlaybackClock(
  timeline: TimelineClock,
  options?: PlaybackClockOptions,
): PlaybackClock {
  return new PlaybackClock(timeline, options);
}
