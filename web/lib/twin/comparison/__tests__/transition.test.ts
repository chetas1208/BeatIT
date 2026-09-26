import assert from "node:assert/strict";
import test from "node:test";
import {
  advanceComparisonTransition,
  createComparisonTransition,
  currentComparisonPresentation,
  pauseComparisonTransition,
  requestComparisonTransition,
} from "@/lib/twin/comparison/transition";

test("animates from one heart to two hearts and settles at the split endpoint", () => {
  const initial = createComparisonTransition({ durationMs: 300 });
  const opening = requestComparisonTransition(initial, "split");
  const halfway = advanceComparisonTransition(opening, 150);
  const complete = advanceComparisonTransition(halfway, 150);

  assert.equal(initial.progress, 0);
  assert.equal(opening.active, true);
  assert.equal(halfway.progress, 0.5);
  assert.equal(currentComparisonPresentation(halfway), "split");
  assert.equal(complete.progress, 1);
  assert.equal(complete.active, false);
  assert.equal(complete.target, "split");
});

test("interrupting a transition reverses from its current frame without resetting it", () => {
  const initial = createComparisonTransition({ durationMs: 400 });
  const opening = requestComparisonTransition(initial, "split");
  const interrupted = advanceComparisonTransition(opening, 100);
  const closing = requestComparisonTransition(interrupted, "single");

  assert.equal(interrupted.progress, 0.25);
  assert.equal(closing.progress, interrupted.progress);
  assert.equal(closing.target, "single");
  assert.equal(closing.active, true);

  const settled = advanceComparisonTransition(closing, 100);
  assert.equal(settled.progress, 0);
  assert.equal(settled.active, false);
  assert.equal(settled.target, "single");
});

test("reduced motion resolves both directions immediately with zero duration", () => {
  const initial = createComparisonTransition({ reducedMotion: true });
  const split = requestComparisonTransition(initial, "split");
  const single = requestComparisonTransition(split, "single");

  assert.equal(split.progress, 1);
  assert.equal(split.durationMs, 0);
  assert.equal(split.active, false);
  assert.equal(split.reducedMotion, true);
  assert.equal(single.progress, 0);
  assert.equal(single.active, false);
  assert.equal(single.reducedMotion, true);
});

test("a zero-duration request settles immediately even when motion is enabled", () => {
  const initial = createComparisonTransition({ durationMs: 0 });
  const split = requestComparisonTransition(initial, "split");

  assert.deepEqual(split, {
    progress: 1,
    target: "split",
    durationMs: 0,
    active: false,
    reducedMotion: false,
  });
});

test("pause freezes progress and does not reset the presentation state", () => {
  const initial = createComparisonTransition({ durationMs: 300 });
  const opening = requestComparisonTransition(initial, "split");
  const halfway = advanceComparisonTransition(opening, 120);
  const paused = pauseComparisonTransition(halfway);
  const afterPause = advanceComparisonTransition(paused, 500);

  assert.equal(paused.progress, 0.4);
  assert.equal(paused.active, false);
  assert.deepEqual(afterPause, paused);
});

test("rejects invalid durations and elapsed times", () => {
  assert.throws(
    () => createComparisonTransition({ durationMs: -1 }),
    /duration must be non-negative/,
  );
  assert.throws(
    () => advanceComparisonTransition(createComparisonTransition(), -1),
    /elapsed time must be non-negative/,
  );
});
