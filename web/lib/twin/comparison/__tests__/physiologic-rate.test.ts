import assert from "node:assert/strict";
import test from "node:test";
import { createCardiacClock } from "@/lib/heart/clock";

function runningClock(heartRateBpm: number) {
  const clock = createCardiacClock(heartRateBpm);
  clock.play();
  return clock;
}

test("independent physiologic-rate clocks drift when heart rates differ", () => {
  const baseline = runningClock(60);
  const scenario = runningClock(90);

  baseline.advance(1000);
  scenario.advance(1000);

  assert.equal(baseline.getState().normalizedPhase, 0);
  assert.equal(scenario.getState().normalizedPhase, 0.5);
  assert.notEqual(
    baseline.getState().normalizedPhase,
    scenario.getState().normalizedPhase,
  );
});

test("independent advancement retains each heart's modeled rate", () => {
  const baseline = runningClock(72);
  const scenario = runningClock(81);

  baseline.advance(1250);
  scenario.advance(1250);

  const baselineState = baseline.getState();
  const scenarioState = scenario.getState();

  assert.equal(baselineState.heartRateBpm, 72);
  assert.equal(scenarioState.heartRateBpm, 81);
  assert.equal(baselineState.cycleDurationMs, 60000 / 72);
  assert.equal(scenarioState.cycleDurationMs, 60000 / 81);
});

test("explicit phase resynchronization aligns phase without changing heart rates", () => {
  const baseline = runningClock(60);
  const scenario = runningClock(90);

  baseline.advance(1000);
  scenario.advance(1000);
  assert.notEqual(
    baseline.getState().normalizedPhase,
    scenario.getState().normalizedPhase,
  );

  baseline.seek(0.25);
  scenario.seek(0.25);

  assert.equal(baseline.getState().normalizedPhase, 0.25);
  assert.equal(scenario.getState().normalizedPhase, 0.25);
  assert.equal(baseline.getState().heartRateBpm, 60);
  assert.equal(scenario.getState().heartRateBpm, 90);
});
