import type { CardiacTwinState } from "@/types/heart";
import type { TwinSnapshot, TwinTimestamp } from "@/lib/twin/time/contracts";

/**
 * A detached state fork created from an observed twin snapshot.
 *
 * The origin fields are intentionally separate from the cloned state so a
 * scenario cannot be mistaken for an observed snapshot. The fork itself and
 * its state are deeply immutable.
 */
export interface SnapshotFork {
  readonly originSnapshotId: TwinSnapshot["id"];
  readonly originTimestamp: TwinTimestamp;
  readonly state: CardiacTwinState;
}

/** Domain-friendly alias for consumers that call the fork a scenario. */
export type ScenarioFork = SnapshotFork;

function cloneValue<T>(value: T): T {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }

  return cloneObjectGraph(value, new WeakMap<object, unknown>());
}

function cloneObjectGraph<T>(value: T, seen: WeakMap<object, unknown>): T {
  if (value === null || typeof value !== "object") {
    return value;
  }

  const existing = seen.get(value);
  if (existing !== undefined) {
    return existing as T;
  }

  const clone = Array.isArray(value) ? [] : {};
  seen.set(value, clone);

  for (const [key, entry] of Object.entries(value)) {
    (clone as Record<string, unknown>)[key] = cloneObjectGraph(entry, seen);
  }

  return clone as T;
}

function deepFreeze<T>(value: T, seen = new WeakSet<object>()): T {
  if (value === null || typeof value !== "object" || seen.has(value)) {
    return value;
  }

  seen.add(value);
  for (const nested of Object.values(value)) {
    deepFreeze(nested, seen);
  }

  return Object.freeze(value);
}

/**
 * Create an immutable scenario fork from an observed snapshot.
 *
 * The original snapshot is never mutated or shared: nested state structures
 * are cloned before being frozen. Origin metadata remains the exact snapshot
 * identity and timestamp so downstream scenario results retain provenance.
 */
export function forkSnapshot(snapshot: TwinSnapshot): SnapshotFork {
  const fork = {
    originSnapshotId: snapshot.id,
    originTimestamp: snapshot.timestamp,
    state: cloneValue(snapshot.state),
  } satisfies SnapshotFork;

  return deepFreeze(fork);
}

/** Explicit constructor alias for call sites that prefer create semantics. */
export const createSnapshotFork = forkSnapshot;
