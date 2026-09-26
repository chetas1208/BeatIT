import assert from "node:assert/strict";
import test from "node:test";
import {
  buildDifferenceMode,
  CHANGED_OPACITY,
  DEFAULT_DIFFERENCE_EPSILON,
  NO_MODELED_DIFFERENCE_TEXT,
  UNCHANGED_OPACITY,
  UNSUPPORTED_OPACITY,
} from "@/lib/twin/comparison/difference-mode";

const orientation = Object.freeze({ azimuthDeg: 18, elevationDeg: 12, rollDeg: 0 });

test("emphasizes changed supported elements and subdues unchanged anatomy", () => {
  const result = buildDifferenceMode([
    { componentId: "left-ventricle", supported: true, delta: 3, orientation },
    { componentId: "aorta", supported: true, delta: 0, orientation },
  ]);

  assert.equal(result.hasModeledDifference, true);
  assert.equal(result.emptyState, null);
  assert.deepEqual(result.elements.map((element) => element.treatment), ["changed", "unchanged"]);
  assert.equal(result.elements[0]?.opacity, CHANGED_OPACITY);
  assert.equal(result.elements[0]?.emphasis, 1);
  assert.equal(result.elements[1]?.opacity, UNCHANGED_OPACITY);
  assert.equal(result.elements[1]?.emphasis, 0);
});

test("keeps unsupported anatomy visible and preserves orientation", () => {
  const result = buildDifferenceMode([
    {
      componentId: "electrical-layer",
      supported: false,
      delta: 99,
      orientation,
    },
  ]);
  const display = result.elements[0];

  assert.equal(display?.treatment, "unsupported");
  assert.equal(display?.changed, false);
  assert.equal(display?.opacity, UNSUPPORTED_OPACITY);
  assert.equal(display?.emphasis, 0);
  assert.strictEqual(display?.orientation, orientation);
  assert.equal(result.hasModeledDifference, false);
});

test("ignores floating-point noise and reports the no-modeled-difference state", () => {
  const result = buildDifferenceMode([
    { componentId: "left-ventricle", supported: true, delta: DEFAULT_DIFFERENCE_EPSILON, orientation },
    {
      componentId: "right-ventricle",
      supported: true,
      deltas: [{ absoluteDelta: null }, Number.NaN],
      orientation,
    },
  ]);

  assert.equal(result.hasModeledDifference, false);
  assert.deepEqual(result.emptyState, {
    kind: "no_modeled_difference",
    text: NO_MODELED_DIFFERENCE_TEXT,
  });
  assert.ok(result.elements.every((element) => element.treatment === "unchanged"));
});

test("does not mutate the input collection or reject valid custom thresholds", () => {
  const input = [
    { componentId: "left-ventricle", supported: true, deltas: [0.2], orientation },
  ] as const;
  const snapshot = structuredClone(input);
  const result = buildDifferenceMode(input, { epsilon: 0.25 });

  assert.deepEqual(input, snapshot);
  assert.equal(result.elements[0]?.treatment, "unchanged");
  assert.throws(
    () => buildDifferenceMode(input, { epsilon: -1 }),
    /finite non-negative number/,
  );
});

test("rejects blank semantic component IDs", () => {
  assert.throws(
    () => buildDifferenceMode([{ componentId: " ", supported: true, delta: 1, orientation }]),
    /non-empty semantic ID/,
  );
});

