import type { CardiacTwinState } from "@/types/heart";
import type {
  StateChangeReason,
  TwinEvent,
  TwinMeasurementPayload,
  TwinStateChange,
} from "@/lib/twin/time/contracts";
import { compareTwinEvents } from "@/lib/twin/time/contracts";

const UNSAFE_PATH_SEGMENTS = new Set(["__proto__", "prototype", "constructor"]);

// Optional leaves are absent from many valid CardiacTwinState instances. They
// may be created only at these known schema locations; arbitrary new fields
// are never introduced by an event.
const OPTIONAL_STATE_PATHS = new Set([
  "patient_context.age_years",
  "patient_context.sex",
  "patient_context.height_cm",
  "patient_context.weight_kg",
  "patient_context.bsa_m2",
  "patient_context.notes",
  "measurements.heart_rate_bpm",
  "measurements.systolic_bp_mmhg",
  "measurements.diastolic_bp_mmhg",
  "measurements.edv_ml",
  "measurements.esv_ml",
  "measurements.ejection_fraction_pct",
  "measurements.stroke_volume_ml",
  "measurements.cardiac_output_l_min",
  "measurements.troponin_ng_l",
  "measurements.bnp_pg_ml",
  "measurements.oxygen_saturation_pct",
  "electrophysiology.rhythm_label",
  "electrophysiology.rr_interval_ms",
  "electrophysiology.qrs_duration_ms",
  "electrophysiology.qt_interval_ms",
  "electrophysiology.qtc_ms",
  "electrophysiology.r_peak_confidence",
  "electrophysiology.conduction_delay_score",
  "electrophysiology.arrhythmia_instability_score",
  "hemodynamics.preload_index",
  "hemodynamics.afterload_index",
  "hemodynamics.contractility_index",
  "hemodynamics.arterial_compliance_index",
  "hemodynamics.systemic_vascular_resistance_index",
  "hemodynamics.filling_pressure_index",
  "hemodynamics.pv_loop_area_index",
  "tissue_state.scar_fraction",
  "tissue_state.inflammation_index",
  "tissue_state.oxygen_delivery_index",
  "tissue_state.myocardial_oxygen_demand_index",
  "tissue_state.stiffness_index",
  "tissue_state.remodeling_index",
  "tissue_state.damage_zone_location",
  "operating_environment.medication_effect_profile",
  "simulation_config.operating.medication_effect_profile",
]);

export type TwinReducerSkipReason =
  | "annotation"
  | "invalid_payload"
  | "unsafe_path"
  | "duplicate";

export interface WearablePayloadHook {
  field: string;
  path: string;
}

export interface TwinStateUpdate extends TwinMeasurementPayload {
  evidenceIds?: readonly string[];
}

export interface TwinReducerOptions {
  wearablePayloadHooks?: readonly WearablePayloadHook[];
}

export interface TwinEventReduction {
  event: TwinEvent;
  state: CardiacTwinState;
  changes: TwinStateChange[];
  applied: boolean;
  skipReason?: TwinReducerSkipReason;
}

export interface TwinReducedEvent extends TwinEventReduction {
  eventId: string;
}

export interface TwinReductionResult {
  state: CardiacTwinState;
  changes: TwinStateChange[];
  appliedEventIds: string[];
  ignoredEventIds: string[];
  events: TwinReducedEvent[];
}

interface StatePathTarget {
  parent: Record<string, unknown>;
  key: string;
  previousValue: unknown;
}

/**
 * Applies one explicit event without mutating the input state or event.
 *
 * Numerical values are treated as opaque evidence. This module intentionally
 * does not infer related measurements, normalize units, or run physiology.
 */
export function reduceTwinEvent(
  state: CardiacTwinState,
  event: TwinEvent,
  options: TwinReducerOptions = {},
): TwinEventReduction {
  const nextState = cloneValue(state);

  if (event.type === "annotation") {
    return { event, state: nextState, changes: [], applied: true, skipReason: "annotation" };
  }

  const payloads = readEventPayloads(event, options);
  if (payloads.length === 0) {
    return { event, state: nextState, changes: [], applied: true };
  }

  const changes: TwinStateChange[] = [];
  for (const payload of payloads) {
    const target = resolveStatePath(nextState, payload.path);
    const nextValue = cloneValue(payload.value);
    if (deepEqual(target.previousValue, nextValue)) continue;

    target.parent[target.key] = nextValue;
    changes.push({
      path: payload.path,
      previousValue: cloneValue(target.previousValue),
      nextValue: cloneValue(nextValue),
      reason: reasonForEvent(event),
      evidenceIds: evidenceIdsFor(event, payload),
    });
  }

  return { event, state: nextState, changes, applied: true };
}

/**
 * Reduces a collection in canonical event order. The input array is never
 * sorted or otherwise modified. Duplicate IDs are applied at most once.
 */
export function reduceTwinEvents(
  initialState: CardiacTwinState,
  events: readonly TwinEvent[],
  options: TwinReducerOptions = {},
): TwinReductionResult {
  const orderedEvents = events
    .map((event) => ({ event }))
    .sort((left, right) => compareTwinEvents(left.event, right.event));

  let state = cloneValue(initialState);
  const changes: TwinStateChange[] = [];
  const appliedEventIds: string[] = [];
  const ignoredEventIds: string[] = [];
  const reducedEvents: TwinReducedEvent[] = [];
  const seenEventIds = new Set<string>();

  for (const { event } of orderedEvents) {
    if (seenEventIds.has(event.id)) {
      ignoredEventIds.push(event.id);
      reducedEvents.push({
        event,
        eventId: event.id,
        state: cloneValue(state),
        changes: [],
        applied: false,
        skipReason: "duplicate",
      });
      continue;
    }
    seenEventIds.add(event.id);

    const reduction = reduceTwinEvent(state, event, options);
    reducedEvents.push({ ...reduction, eventId: event.id });
    if (!reduction.applied) {
      ignoredEventIds.push(event.id);
      continue;
    }

    state = reduction.state;
    changes.push(...reduction.changes);
    appliedEventIds.push(event.id);
  }

  return { state, changes, appliedEventIds, ignoredEventIds, events: reducedEvents };
}

/** Returns a deep clone suitable for preserving snapshot immutability. */
export function cloneTwinState(state: CardiacTwinState): CardiacTwinState {
  return cloneValue(state);
}

function readMeasurementPayload(payload: unknown): TwinStateUpdate | null {
  if (!isRecord(payload) || typeof payload.path !== "string" || payload.path.length === 0) {
    return null;
  }
  if (!Object.prototype.hasOwnProperty.call(payload, "value")) {
    return null;
  }

  return {
    path: payload.path,
    value: payload.value,
    ...(typeof payload.unit === "string" ? { unit: payload.unit } : {}),
    ...(isRecord(payload.provenance)
      ? { provenance: payload.provenance as unknown as TwinMeasurementPayload["provenance"] }
      : {}),
    ...(Array.isArray(payload.evidenceIds)
      ? { evidenceIds: payload.evidenceIds.filter((id): id is string => typeof id === "string") }
      : {}),
  };
}

function readEventPayloads(
  event: TwinEvent,
  options: TwinReducerOptions,
): TwinStateUpdate[] {
  if (event.type === "wearable_sample") {
    const payload = event.payload;
    if (isRecord(payload) && typeof payload.path === "string" && Object.prototype.hasOwnProperty.call(payload, "value")) {
      const explicitPayload = readMeasurementPayload(payload);
      if (!explicitPayload) throw new Error(`Invalid Twin event payload for ${event.id}`);
      return [explicitPayload];
    }
    if (!isRecord(payload)) return [];

    if (Array.isArray(payload.updates)) {
      return payload.updates
        .map((update) => readMeasurementPayload(update))
        .filter((update): update is TwinStateUpdate => update !== null);
    }

    return (options.wearablePayloadHooks ?? [])
      .filter((hook) => Object.prototype.hasOwnProperty.call(payload, hook.field))
      .map((hook) => ({
        path: hook.path,
        value: payload[hook.field],
        evidenceIds: [event.id, ...(event.provenance.evidenceIds ?? [])],
      }));
  }

  // Narrative evidence can be meaningful without changing the numerical
  // state. Preserve its event/provenance in the timeline as a no-op.
  if (event.type === "clinical_evidence") {
    const payload = event.payload;
    return isRecord(payload) && typeof payload.path === "string"
      ? [readMeasurementPayload(payload)].filter((item): item is TwinStateUpdate => item !== null)
      : [];
  }

  if (isRecord(event.payload) && Array.isArray(event.payload.updates)) {
    return event.payload.updates
      .map((update) => readMeasurementPayload(update))
      .filter((update): update is TwinStateUpdate => update !== null);
  }

  const measurement = readMeasurementPayload(event.payload);
  if (!measurement) {
    throw new Error(`Invalid Twin event payload for ${event.id}`);
  }
  return [measurement];
}

/** Creates an explicit allow-list mapping from vendor fields to state paths. */
export function createWearablePayloadHook(
  fields: Readonly<Record<string, string>>,
): WearablePayloadHook[] {
  return Object.entries(fields).map(([field, path]) => ({ field, path }));
}

function resolveStatePath(state: CardiacTwinState, path: string): StatePathTarget {
  const segments = path.split(".");
  if (
    segments.length === 0 ||
    segments.some((segment) => segment.length === 0 || UNSAFE_PATH_SEGMENTS.has(segment))
  ) {
    throw new Error(`Unsafe or invalid Twin state path: ${path}`);
  }

  let current: unknown = state;
  for (const segment of segments.slice(0, -1)) {
    if (!isRecord(current) || !Object.prototype.hasOwnProperty.call(current, segment)) {
      throw new Error(`Twin state path is outside CardiacTwinState: ${path}`);
    }
    current = current[segment];
  }

  if (!isRecord(current)) {
    throw new Error(`Twin state path is outside CardiacTwinState: ${path}`);
  }

  const key = segments[segments.length - 1];
  const exists = Object.prototype.hasOwnProperty.call(current, key);
  if (!exists && !OPTIONAL_STATE_PATHS.has(path)) {
    throw new Error(`Twin state path is outside CardiacTwinState: ${path}`);
  }

  return {
    parent: current,
    key,
    previousValue: current[key],
  };
}

function reasonForEvent(event: TwinEvent): StateChangeReason {
  return event.type === "state_update" ? "deterministic_derivation" : "new_evidence";
}

function evidenceIdsFor(event: TwinEvent, payload: TwinStateUpdate): string[] {
  const ids = [
    event.id,
    ...(event.provenance.evidenceIds ?? []),
    ...(payload.provenance?.evidenceIds ?? []),
    ...(payload.evidenceIds ?? []),
  ];
  return [...new Set(ids.filter((id): id is string => typeof id === "string" && id.length > 0))];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function cloneValue<T>(value: T): T {
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map((item) => cloneValue(item)) as T;

  const source = value as Record<string, unknown>;
  const clone: Record<string, unknown> = {};
  for (const key of Object.keys(source)) {
    clone[key] = cloneValue(source[key]);
  }
  return clone as T;
}

function deepEqual(left: unknown, right: unknown): boolean {
  if (Object.is(left, right)) return true;
  if (typeof left !== typeof right || left === null || right === null) return false;
  if (Array.isArray(left) || Array.isArray(right)) {
    if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) return false;
    return left.every((value, index) => deepEqual(value, right[index]));
  }
  if (typeof left !== "object" || typeof right !== "object") return false;

  const leftRecord = left as Record<string, unknown>;
  const rightRecord = right as Record<string, unknown>;
  const leftKeys = Object.keys(leftRecord);
  const rightKeys = Object.keys(rightRecord);
  if (leftKeys.length !== rightKeys.length) return false;
  return leftKeys.every(
    (key) => Object.prototype.hasOwnProperty.call(rightRecord, key) && deepEqual(leftRecord[key], rightRecord[key]),
  );
}
