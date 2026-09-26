import assert from "node:assert/strict";
import test from "node:test";
import {
  TwinEventStore,
  TwinEventValidationError,
  isTwinCorrectionEvent,
  type TwinCorrectionInput,
} from "@/lib/twin/events";
import type { TwinEvent } from "@/lib/twin/time/contracts";

const provenance = {
  source: "clinical_record" as const,
  sourceId: "record-1",
  confidence: 0.9,
  evidenceIds: ["evidence-1"],
};

function event(overrides: Partial<TwinEvent> = {}): TwinEvent {
  return {
    id: "event-1",
    timestamp: "2026-09-26T10:00:00.000Z",
    type: "measurement",
    source: "clinical_record",
    payload: { path: "measurements.ejection_fraction_pct", value: 48, unit: "%" },
    provenance,
    ...overrides,
  };
}

test("orders out-of-order events by timestamp and preserves insertion order for ties", () => {
  const store = new TwinEventStore();
  store.append(event({ id: "late", timestamp: "2026-09-26T10:02:00Z" }));
  store.append(event({ id: "early", timestamp: "2026-09-26T09:00:00Z" }));
  store.append(event({ id: "same-time-first", timestamp: "2026-09-26T10:01:00Z" }));
  store.append(event({ id: "same-time-second", timestamp: "2026-09-26T10:01:00+00:00" }));

  assert.deepEqual(
    store.getEvents().map(({ id }) => id),
    ["early", "same-time-first", "same-time-second", "late"],
  );
  assert.equal(store.size, 4);
});

test("makes stored events and nested payloads immutable and isolates caller data", () => {
  const payload = { path: "measurements.heart_rate_bpm", value: 72, metadata: { source: "watch" } };
  const input = event({ id: "immutable", payload });
  const store = new TwinEventStore();
  const result = store.append(input);

  payload.metadata.source = "changed-after-append";
  assert.equal((result.event.payload as typeof payload).metadata.source, "watch");
  assert.equal(Object.isFrozen(result.event), true);
  assert.equal(Object.isFrozen(result.event.payload), true);
  assert.throws(() => {
    (result.event.payload as { value: number }).value = 99;
  }, TypeError);
});

test("treats an identical event ID as an idempotent duplicate", () => {
  const store = new TwinEventStore([event({ id: "duplicate" })]);
  const result = store.append(event({ id: "duplicate" }));

  assert.equal(result.status, "duplicate");
  assert.equal(store.size, 1);
  assert.equal(result.event, store.get("duplicate"));
});

test("rejects reuse of an event ID with different content", () => {
  const store = new TwinEventStore([event({ id: "conflict" })]);

  assert.throws(
    () => store.append(event({ id: "conflict", payload: { path: "measurements.heart_rate_bpm", value: 88 } })),
    (error: unknown) => error instanceof TwinEventValidationError && error.field === "id",
  );
  assert.equal(store.size, 1);
});

test("validates timestamps, provenance, payload JSON, and event enums", () => {
  const store = new TwinEventStore();
  const invalidCases: Array<[string, TwinEvent]> = [
    ["timestamp", event({ timestamp: "2026-09-26T10:00:00" })],
    ["source", event({ source: "unknown" as TwinEvent["source"] })],
    ["type", event({ type: "unknown" as TwinEvent["type"] })],
    ["provenance.confidence", event({ provenance: { ...provenance, confidence: 1.1 } })],
    ["payload", event({ payload: { value: Number.NaN } })],
  ];

  for (const [field, invalidEvent] of invalidCases) {
    assert.throws(
      () => store.append(invalidEvent),
      (error: unknown) => error instanceof TwinEventValidationError && error.field === field,
    );
  }
  assert.equal(store.size, 0);
});

test("appends explicit correction events referencing an existing event", () => {
  const store = new TwinEventStore([event({ id: "measurement-1" })]);
  const correction: TwinCorrectionInput = {
    id: "correction-1",
    timestamp: "2026-09-26T10:05:00Z",
    source: "clinical_record",
    correctionOf: "measurement-1",
    path: "measurements.ejection_fraction_pct",
    value: 51,
    correctionReason: "Signed addendum supersedes the preliminary value.",
    provenance: { sourceId: "addendum-1", evidenceIds: ["evidence-2"] },
  };

  const result = store.appendCorrection(correction);
  assert.equal(result.status, "appended");
  assert.equal(isTwinCorrectionEvent(result.event), true);
  if (isTwinCorrectionEvent(result.event)) {
    assert.deepEqual(result.event.payload, {
      path: correction.path,
      value: correction.value,
      correctionOf: "measurement-1",
      correctionReason: correction.correctionReason,
    });
  }
  assert.deepEqual(store.getEvents().map(({ id }) => id), ["measurement-1", "correction-1"]);
  assert.throws(
    () => store.appendCorrection({ ...correction, id: "bad-correction", correctionOf: "missing" }),
    (error: unknown) => error instanceof TwinEventValidationError && error.field === "correctionOf",
  );
});

test("serializes and imports a deterministic immutable event log", () => {
  const store = new TwinEventStore();
  store.append(event({ id: "second", timestamp: "2026-09-26T10:02:00Z" }));
  store.append(event({ id: "first", timestamp: "2026-09-26T10:01:00Z" }));

  const serialized = store.serialize();
  const restored = TwinEventStore.fromJSON(serialized);
  assert.deepEqual(restored.export(), store.export());
  assert.equal(Object.isFrozen(restored.getEvents()[0]), true);
  assert.throws(
    () => TwinEventStore.fromJSON(JSON.stringify({ version: 2, events: [] })),
    (error: unknown) => error instanceof TwinEventValidationError && error.field === "serialized",
  );
});
