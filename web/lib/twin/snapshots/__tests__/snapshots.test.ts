import assert from "node:assert/strict";
import test from "node:test";
import type { TwinEvent, TwinSnapshot } from "@/lib/twin/time/contracts";
import {
  cloneSnapshot,
  reconstructTimeline,
} from "@/lib/twin/snapshots";
import { createFixtureState, measured } from "@/lib/heart/__tests__/fixtures";

function event(overrides: Partial<TwinEvent> = {}): TwinEvent {
  return {
    id: "echo-1",
    timestamp: "2026-09-26T01:00:00Z",
    type: "measurement",
    source: "imaging",
    payload: {
      path: "measurements.ejection_fraction_pct",
      value: measured(51, "%", "file_extraction"),
    },
    provenance: {
      source: "imaging",
      sourceId: "echo-1",
      evidenceIds: ["evidence:echo-1"],
    },
    ...overrides,
  };
}

test("reconstructs ordered immutable snapshots with stable IDs and changes", () => {
  const initialState = createFixtureState();
  const events = [
    event({ id: "echo-2", timestamp: "2026-09-26T02:00:00Z" }),
    event({ id: "echo-1", timestamp: "2026-09-26T01:00:00Z" }),
  ];

  const first = reconstructTimeline(initialState, events);
  const second = reconstructTimeline(initialState, events);

  assert.deepEqual(first.snapshots.map((snapshot) => snapshot.timestamp), [
    initialState.created_at,
    "2026-09-26T01:00:00Z",
    "2026-09-26T02:00:00Z",
  ]);
  assert.deepEqual(
    first.snapshots.map((snapshot) => snapshot.id),
    second.snapshots.map((snapshot) => snapshot.id),
  );
  assert.equal(first.snapshots[1]?.changedFields[0]?.path, "measurements.ejection_fraction_pct");
  assert.deepEqual(first.snapshots[1]?.changedFields[0]?.evidenceIds, ["echo-1", "evidence:echo-1"]);
  assert.deepEqual(first.snapshots[1]?.provenance, [events[1]!.provenance]);
  assert.equal(first.currentSnapshotId, first.snapshots[2]?.id);
  assert.equal(first.startTime, initialState.created_at);
  assert.equal(first.endTime, "2026-09-26T02:00:00Z");
});

test("does not mutate the initial state or event payloads", () => {
  const initialState = createFixtureState();
  const sourceEvent = event();
  const originalState = structuredClone(initialState);
  const originalEvent = structuredClone(sourceEvent);

  const timeline = reconstructTimeline(initialState, [sourceEvent]);
  assert.deepEqual(initialState, originalState);
  assert.deepEqual(sourceEvent, originalEvent);
  assert.notEqual(timeline.snapshots[1]!.state, initialState);
  assert.notEqual(timeline.snapshots[1]!.state.measurements, initialState.measurements);
  assert.throws(() => {
    (timeline.snapshots[1]!.state.measurements as { ejection_fraction_pct?: unknown }).ejection_fraction_pct = null;
  }, TypeError);
  assert.throws(() => {
    (timeline.snapshots as TwinSnapshot[]).push(timeline.snapshots[0]!);
  }, TypeError);
});

test("preserves explicit visualization, synthetic quality, and historical provenance", () => {
  const visualization = {
    cardiac_cycle: { time_ms: [0], volume_ml: [1], pressure_mmhg: [2], aortic_flow_ml_s: [3], heart_rate_bpm: 60, cycle_duration_ms: 1000 },
    pv_loop: { volume_ml: [1], pressure_mmhg: [2], pv_loop_area_mmhg_ml: 1, stroke_work_j: 1, peak_pressure_mmhg: 2 },
    summary: { stroke_volume_ml: 1, ef_pct: 2, cardiac_output_l_min: 3, heart_rate_bpm: 60, map_mmhg: 80, operating_mode: "rest" as const },
    hemodynamics: {},
    electrophysiology: {},
    simulation_note: "synthetic replay",
  };
  const timeline = reconstructTimeline(createFixtureState(), [
    event({
      id: "replay-1",
      source: "synthetic_replay",
      type: "state_update",
      payload: { visualization, path: "measurements.heart_rate_bpm", value: measured(72, "bpm", "derived") },
      provenance: { source: "synthetic_replay", sourceId: "fixture-1", note: "DEMO STREAM" },
    }),
    event({
      id: "annotation-1",
      timestamp: "2026-09-26T03:00:00Z",
      type: "annotation",
      source: "user_annotation",
      payload: { text: "reviewed" },
      provenance: { source: "user_annotation", sourceId: "reviewer-1" },
    }),
  ]);

  assert.equal(timeline.snapshots[1]?.quality, "synthetic");
  assert.equal(timeline.snapshots[1]?.visualization?.simulation_note, "synthetic replay");
  assert.equal(timeline.snapshots[2]?.visualization?.simulation_note, "synthetic replay");
  assert.equal(timeline.snapshots[2]?.quality, "synthetic");
  assert.equal(timeline.snapshots[2]?.changedFields.length, 0);
  assert.equal(timeline.snapshots[2]?.provenance.some((item) => item.source === "synthetic_replay"), true);
});

test("supports a canonical reducer without sharing mutable reducer output", () => {
  const initialState = createFixtureState();
  const timeline = reconstructTimeline(initialState, [event()], {
    reducer: (state, currentEvent) => ({
      state: {
        ...state,
        measurements: {
          ...state.measurements,
          heart_rate_bpm: measured(70, "bpm"),
        },
      },
      changes: [{
        path: "measurements.heart_rate_bpm",
        previousValue: null,
        nextValue: measured(70, "bpm"),
        reason: "deterministic_derivation",
        evidenceIds: [currentEvent.id],
      }],
      quality: "derived",
    }),
  });

  assert.equal(timeline.snapshots[1]?.quality, "derived");
  assert.equal(timeline.snapshots[1]?.changedFields[0]?.reason, "deterministic_derivation");
  assert.notEqual(timeline.snapshots[1]?.state, initialState);
});

test("cloneSnapshot returns an immutable detached snapshot with the same identity", () => {
  const snapshot = reconstructTimeline(createFixtureState(), [event()]).snapshots[1]!;
  const clone = cloneSnapshot(snapshot);
  assert.deepEqual(clone, snapshot);
  assert.notEqual(clone, snapshot);
  assert.notEqual(clone.state, snapshot.state);
  assert.equal(clone.id, snapshot.id);
});
