import assert from "node:assert/strict";
import test from "node:test";
import {
  advanceComparisonClock,
  createComparisonClock,
  playComparisonClock,
} from "@/lib/twin/comparison/clock";
import {
  projectComparisonPVCursors,
  projectPVCursor,
  PV_UNCERTAINTY_LIMITATION,
} from "@/lib/twin/comparison/pv";
import type { PVLoopData } from "@/types/heart";

function loop(): PVLoopData {
  return {
    volume_ml: [90, 110, 130, 100],
    pressure_mmhg: [12, 80, 120, 20],
    pv_loop_area_mmhg_ml: 1000,
    stroke_work_j: 100,
    peak_pressure_mmhg: 120,
  };
}

test("projects independent baseline and scenario phases from the comparison clock", () => {
  const clock = advanceComparisonClock(
    playComparisonClock(
      createComparisonClock(
        { baselineHeartRateBpm: 60, scenarioHeartRateBpm: 90 },
        { mode: "physiologic_rate" },
      ),
    ),
    { elapsedMs: 1000 },
  );

  const projection = projectComparisonPVCursors(clock, loop(), loop());

  assert.equal(projection.baseline.phase, 0);
  assert.equal(projection.scenario.phase, 0.5);
  assert.equal(projection.baseline.cursorIndex, 0);
  assert.equal(projection.scenario.cursorIndex, 2);
  assert.deepEqual(
    [projection.baseline.volumeMl, projection.baseline.pressureMmhg],
    [90, 12],
  );
  assert.deepEqual(
    [projection.scenario.volumeMl, projection.scenario.pressureMmhg],
    [130, 120],
  );
});

test("uses a phase-locked clock phase for both PV cursors", () => {
  const clock = createComparisonClock(
    { baselineHeartRateBpm: 72, scenarioHeartRateBpm: 81 },
    { mode: "phase_locked", normalizedPhase: 0.75 },
  );

  const projection = projectComparisonPVCursors(clock, loop(), loop());

  assert.equal(projection.baseline.phase, 0.75);
  assert.equal(projection.scenario.phase, 0.75);
  assert.equal(projection.baseline.cursorIndex, 3);
  assert.equal(projection.scenario.cursorIndex, 3);
});

test("normalizes wrapped phases before selecting a source point", () => {
  const positive = projectPVCursor(loop(), 1.25);
  const negative = projectPVCursor(loop(), -0.25);

  assert.equal(positive.phase, 0.25);
  assert.equal(positive.cursorIndex, 1);
  assert.equal(negative.phase, 0.75);
  assert.equal(negative.cursorIndex, 3);
});

test("does not mutate or rescale the held source loops", () => {
  const baseline = loop();
  const scenario = loop();
  const before = structuredClone({ baseline, scenario });

  projectComparisonPVCursors(
    createComparisonClock({ baselineHeartRateBpm: 72, scenarioHeartRateBpm: 81 }),
    baseline,
    scenario,
  );

  assert.deepEqual({ baseline, scenario }, before);
});

test("preserves the scalar-only uncertainty boundary", () => {
  const projection = projectComparisonPVCursors(
    createComparisonClock({ baselineHeartRateBpm: 72, scenarioHeartRateBpm: 81 }),
    loop(),
    loop(),
  );

  assert.deepEqual(projection.uncertainty, {
    mode: "scalar_pv_linked",
    pointwiseLoopAvailable: false,
    heldShape: true,
    limitation: PV_UNCERTAINTY_LIMITATION,
  });
});

test("fails closed when a loop cannot provide aligned finite points", () => {
  const invalid = { ...loop(), pressure_mmhg: [12] };
  const cursor = projectPVCursor(invalid, 0.5);

  assert.deepEqual(cursor, {
    phase: 0.5,
    available: false,
    cursorIndex: null,
    volumeMl: null,
    pressureMmhg: null,
  });
});

test("fails closed when a loop is missing its point arrays", () => {
  const cursor = projectPVCursor({ ...loop(), volume_ml: undefined } as unknown as PVLoopData, 0.5);

  assert.equal(cursor.available, false);
  assert.equal(cursor.cursorIndex, null);
  assert.equal(cursor.volumeMl, null);
  assert.equal(cursor.pressureMmhg, null);
});
