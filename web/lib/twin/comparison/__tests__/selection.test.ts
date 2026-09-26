import assert from "node:assert/strict";
import test from "node:test";
import { HeartComponentRegistry } from "@/lib/heart/registry";
import {
  clearComparisonSelection,
  counterpartComponentId,
  EMPTY_COMPARISON_SELECTION,
  selectComparisonComponent,
  selectLinkedComponent,
  selectUnlinkedComponent,
  type ComparisonSelectionState,
} from "@/lib/twin/comparison/selection";

test("counterparts use registered semantic IDs rather than mesh names", () => {
  const componentIds = ["left-ventricle", "mitral-valve", "aha-13", "lad", "sa-node"];

  for (const componentId of componentIds) {
    assert.ok(HeartComponentRegistry.getComponent(componentId));
    assert.equal(counterpartComponentId(componentId), componentId);
  }

  assert.throws(() => counterpartComponentId("leftVentricleMesh"), RangeError);
  assert.throws(() => counterpartComponentId(""), RangeError);
});

test("linked selection highlights one semantic component in both hearts", () => {
  assert.deepEqual(selectLinkedComponent("left-ventricle"), {
    baselineComponentId: "left-ventricle",
    scenarioComponentId: "left-ventricle",
  });

  const selectedFromScenario = selectComparisonComponent(
    EMPTY_COMPARISON_SELECTION,
    "scenario",
    "aha-13",
    "linked",
  );

  assert.deepEqual(selectedFromScenario, {
    baselineComponentId: "aha-13",
    scenarioComponentId: "aha-13",
  });
});

test("unlinked selection changes only the clicked heart", () => {
  const initial: ComparisonSelectionState = {
    baselineComponentId: "left-ventricle",
    scenarioComponentId: "right-ventricle",
  };

  const baselineSelected = selectUnlinkedComponent(initial, "baseline", "aorta");
  const scenarioSelected = selectComparisonComponent(
    initial,
    "scenario",
    "pulmonary-artery",
    "unlinked",
  );

  assert.deepEqual(baselineSelected, {
    baselineComponentId: "aorta",
    scenarioComponentId: "right-ventricle",
  });
  assert.deepEqual(scenarioSelected, {
    baselineComponentId: "left-ventricle",
    scenarioComponentId: "pulmonary-artery",
  });
  assert.deepEqual(initial, {
    baselineComponentId: "left-ventricle",
    scenarioComponentId: "right-ventricle",
  });
  assert.notEqual(baselineSelected, initial);
  assert.notEqual(scenarioSelected, initial);
});

test("clearing respects linked and unlinked modes without mutation", () => {
  const state: ComparisonSelectionState = Object.freeze({
    baselineComponentId: "aha-13",
    scenarioComponentId: "aha-13",
  });

  const baselineCleared = clearComparisonSelection(state, "baseline");
  const linkedCleared = clearComparisonSelection(state, "scenario", "linked");

  assert.deepEqual(baselineCleared, {
    baselineComponentId: null,
    scenarioComponentId: "aha-13",
  });
  assert.deepEqual(linkedCleared, EMPTY_COMPARISON_SELECTION);
  assert.deepEqual(state, {
    baselineComponentId: "aha-13",
    scenarioComponentId: "aha-13",
  });
  assert.notEqual(baselineCleared, state);
  assert.notEqual(linkedCleared, state);
});

test("selection rejects unknown IDs, unsupported sides, and unsupported modes", () => {
  assert.throws(() => selectLinkedComponent("   "), RangeError);
  assert.throws(
    () => selectUnlinkedComponent(EMPTY_COMPARISON_SELECTION, "other" as never, "aorta"),
    RangeError,
  );
  assert.throws(
    () => selectComparisonComponent(EMPTY_COMPARISON_SELECTION, "baseline", "aorta", "other" as never),
    RangeError,
  );
  assert.throws(
    () => selectComparisonComponent(EMPTY_COMPARISON_SELECTION, "other" as never, "aorta", "linked"),
    RangeError,
  );
  assert.throws(
    () => clearComparisonSelection(EMPTY_COMPARISON_SELECTION, "baseline", "other" as never),
    RangeError,
  );
});
