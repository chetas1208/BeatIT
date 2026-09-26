import assert from "node:assert/strict";
import test from "node:test";
import {
  advanceComparisonClock,
  createComparisonClock,
  pauseComparisonClock,
  playComparisonClock,
  resetComparisonClock,
  seekComparisonClock,
} from "@/lib/twin/comparison/clock";

function createPhaseLockedClock() {
  return createComparisonClock(
    {
      baselineHeartRateBpm: 72,
      scenarioHeartRateBpm: 81,
    },
    {
      mode: "phase_locked",
      playbackSpeed: 1,
    },
  );
}

test("phase_locked keeps both rendered hearts at the same phase despite different HR", () => {
  const clock = playComparisonClock(createPhaseLockedClock());

  const state = advanceComparisonClock(clock, { elapsedMs: 250 });

  assert.equal(state.mode, "phase_locked");
  assert.equal(state.baselineHeartRateBpm, 72);
  assert.equal(state.scenarioHeartRateBpm, 81);
  assert.notEqual(state.baselineHeartRateBpm, state.scenarioHeartRateBpm);
  assert.equal(state.baselinePhase, state.scenarioPhase);
  assert.equal(state.baselinePhase, state.normalizedPhase);
});

test("phase_locked seek updates both heart phases together", () => {
  const clock = playComparisonClock(createPhaseLockedClock());

  const state = seekComparisonClock(clock, 0.62);

  assert.ok(Math.abs(state.normalizedPhase - 0.62) < 1e-12);
  assert.equal(state.baselinePhase, state.normalizedPhase);
  assert.equal(state.scenarioPhase, state.normalizedPhase);
});

test("pause freezes a phase-locked comparison and reset returns both hearts to zero", () => {
  const clock = playComparisonClock(createPhaseLockedClock());

  const beforePause = advanceComparisonClock(clock, { elapsedMs: 400 });
  const paused = pauseComparisonClock(beforePause);
  const afterPause = advanceComparisonClock(paused, { elapsedMs: 400 });

  assert.equal(paused.playing, false);
  assert.deepEqual(afterPause, paused);
  assert.equal(afterPause.baselinePhase, afterPause.scenarioPhase);

  const reset = resetComparisonClock(paused);
  assert.equal(reset.normalizedPhase, 0);
  assert.equal(reset.baselinePhase, 0);
  assert.equal(reset.scenarioPhase, 0);
  assert.equal(reset.playing, false);
  assert.notEqual(beforePause.normalizedPhase, 0);
});

test("clock controls do not mutate the input configuration", () => {
  const rates = {
    baselineHeartRateBpm: 72,
    scenarioHeartRateBpm: 81,
  };
  const options = {
    mode: "phase_locked" as const,
    playbackSpeed: 2,
  };
  const originalRates = structuredClone(rates);
  const originalOptions = structuredClone(options);
  const initial = createComparisonClock(rates, options);
  const originalState = structuredClone(initial);

  const played = playComparisonClock(initial);
  const sought = seekComparisonClock(played, 0.37);
  const paused = pauseComparisonClock(sought);
  resetComparisonClock(paused);

  assert.deepEqual(rates, originalRates);
  assert.deepEqual(options, originalOptions);
  assert.deepEqual(initial, originalState);
});
