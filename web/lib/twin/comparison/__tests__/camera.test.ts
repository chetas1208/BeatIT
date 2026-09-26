import assert from "node:assert/strict";
import test from "node:test";
import {
  clearComparisonCameraFocus,
  createComparisonCameraState,
  focusComparisonCamera,
  getComparisonCameraPane,
  resetComparisonCamera,
  setComparisonCameraMode,
  setComparisonCameraPose,
} from "@/lib/twin/comparison/camera";

const leftVentricle = {
  componentId: "left-ventricle",
  target: [0.2, -0.2, 0] as const,
  distance: 3.25,
};

test("linked cameras mirror pose updates and preserve stable orientation", () => {
  const initial = createComparisonCameraState();
  const pose = {
    target: [0.2, -0.2, 0] as const,
    distance: 3.5,
    orientation: { azimuthDeg: 35, elevationDeg: 12, rollDeg: 0 },
  };

  const next = setComparisonCameraPose(initial, "baseline", pose);

  assert.deepEqual(next.baseline.pose, next.counterfactual.pose);
  assert.equal(next.baseline.pose.orientation.rollDeg, 0);
  assert.equal(next.baseline.focusedComponentId, null);
  assert.equal(next.counterfactual.focusedComponentId, null);
  assert.deepEqual(initial.baseline.pose, initial.counterfactual.pose);
});

test("independent mode isolates camera pose and semantic focus", () => {
  const independent = setComparisonCameraMode(createComparisonCameraState(), "independent");
  const focused = focusComparisonCamera(independent, "baseline", leftVentricle);
  const rotated = setComparisonCameraPose(focused, "counterfactual", {
    ...focused.counterfactual.pose,
    orientation: { azimuthDeg: -40, elevationDeg: 8, rollDeg: 0 },
  });

  assert.equal(focused.baseline.focusedComponentId, "left-ventricle");
  assert.equal(focused.counterfactual.focusedComponentId, null);
  assert.equal(rotated.baseline.pose.orientation.azimuthDeg, 0);
  assert.equal(rotated.counterfactual.pose.orientation.azimuthDeg, -40);
  assert.notDeepEqual(rotated.baseline.pose, rotated.counterfactual.pose);
});

test("linked semantic focus targets corresponding anatomy without changing orientation", () => {
  const initial = createComparisonCameraState();
  const focused = focusComparisonCamera(initial, "baseline", leftVentricle);

  assert.equal(focused.baseline.focusedComponentId, "left-ventricle");
  assert.equal(focused.counterfactual.focusedComponentId, "left-ventricle");
  assert.deepEqual(focused.baseline.pose.orientation, initial.baseline.pose.orientation);
  assert.deepEqual(focused.counterfactual.pose.orientation, initial.counterfactual.pose.orientation);
  assert.equal(focused.baseline.pose.distance, 3.25);
});

test("reset clears focus and returns both cameras to the canonical pose", () => {
  const state = focusComparisonCamera(createComparisonCameraState(), "counterfactual", leftVentricle);
  const reset = resetComparisonCamera(state);
  const fresh = createComparisonCameraState();

  assert.equal(reset.mode, state.mode);
  assert.deepEqual(reset, fresh);
});

test("focus clearing and snapshots do not mutate camera state", () => {
  const state = focusComparisonCamera(createComparisonCameraState(), "baseline", leftVentricle);
  const snapshot = getComparisonCameraPane(state, "baseline");
  const cleared = clearComparisonCameraFocus(state, "baseline");

  assert.equal(snapshot.focusedComponentId, "left-ventricle");
  assert.equal(cleared.baseline.focusedComponentId, null);
  assert.equal(state.baseline.focusedComponentId, "left-ventricle");
  assert.notStrictEqual(snapshot.pose.target, state.baseline.pose.target);
});

test("invalid semantic IDs, distances, and orientations fail explicitly", () => {
  assert.throws(
    () => focusComparisonCamera(createComparisonCameraState(), "baseline", { ...leftVentricle, componentId: " " }),
    /semantic component ID/,
  );
  assert.throws(
    () => focusComparisonCamera(createComparisonCameraState(), "baseline", { ...leftVentricle, distance: 0 }),
    /distance must be positive/,
  );
  assert.throws(
    () => setComparisonCameraPose(createComparisonCameraState(), "baseline", {
      ...createComparisonCameraState().baseline.pose,
      orientation: { azimuthDeg: 0, elevationDeg: 91, rollDeg: 0 },
    }),
    /elevation must be between/,
  );
});
