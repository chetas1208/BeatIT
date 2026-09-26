import assert from "node:assert/strict";
import test from "node:test";
import {
  advanceComparisonClock,
  createComparisonClock,
  pauseComparisonClock,
  playComparisonClock,
  seekComparisonClock,
} from "@/lib/twin/comparison/clock";

const RATES = {
  baselineHeartRateBpm: 60,
  scenarioHeartRateBpm: 90,
} as const;

function assertPhaseClose(actual: number, expected: number): void {
  assert.ok(Math.abs(actual - expected) < 1e-12, `${actual} is not near ${expected}`);
}

test("phase_locked keeps both PV cursors identical while advancing", () => {
  const clock = playComparisonClock(
    createComparisonClock(RATES, { mode: "phase_locked" }),
  );

  const advanced = advanceComparisonClock(clock, { elapsedMs: 500 });

  assert.equal(advanced.baselinePhase, 0.5);
  assert.equal(advanced.scenarioPhase, advanced.baselinePhase);
  assert.equal(advanced.normalizedPhase, advanced.baselinePhase);
});

test("phase_locked seek re-aligns both PV cursors and pause freezes them", () => {
  const running = playComparisonClock(
    createComparisonClock(RATES, {
      mode: "phase_locked",
      normalizedPhase: 0.2,
    }),
  );
  const sought = seekComparisonClock(running, 0.75);
  const paused = pauseComparisonClock(sought);
  const afterPause = advanceComparisonClock(paused, { elapsedMs: 1000 });

  assert.equal(sought.baselinePhase, 0.75);
  assert.equal(sought.scenarioPhase, 0.75);
  assert.equal(paused.playing, false);
  assert.deepEqual(afterPause, paused);
});

test("physiologic_rate advances each PV cursor at its respective heart rate", () => {
  const clock = playComparisonClock(
    createComparisonClock(RATES, { mode: "physiologic_rate" }),
  );

  const advanced = advanceComparisonClock(clock, { elapsedMs: 500 });

  assert.equal(advanced.baselinePhase, 0.5);
  assert.equal(advanced.scenarioPhase, 0.75);
  assert.equal(advanced.normalizedPhase, advanced.baselinePhase);
  assert.notEqual(advanced.baselinePhase, advanced.scenarioPhase);
});

test("physiologic_rate seek re-aligns cursors, then pause preserves independent phases", () => {
  const running = playComparisonClock(
    createComparisonClock(RATES, { mode: "physiologic_rate" }),
  );
  const sought = seekComparisonClock(running, 0.4);
  const advanced = advanceComparisonClock(sought, { elapsedMs: 500 });
  const paused = pauseComparisonClock(advanced);
  const afterPause = advanceComparisonClock(paused, { elapsedMs: 1000 });

  assertPhaseClose(sought.baselinePhase, 0.4);
  assertPhaseClose(sought.scenarioPhase, 0.4);
  assertPhaseClose(advanced.baselinePhase, 0.9);
  assertPhaseClose(advanced.scenarioPhase, 0.15);
  assert.equal(paused.playing, false);
  assert.deepEqual(afterPause, paused);
});
