import assert from "node:assert/strict";
import test from "node:test";
import { HEART_COMPONENTS, HeartComponentRegistry } from "@/lib/heart/registry";
import {
  createInteractionController,
  clearFocus,
  clearHover,
  EMPTY_HEART_SELECTION,
  focusComponent,
  hoverComponent,
  resetHeartInteraction,
  selectComponent,
} from "@/components/heart/interaction/selection";
import { getSemanticComponentId, getSemanticComponentIdFromEvent } from "@/components/heart/interaction/picking";

test("registry has stable unique anatomy, electrical, functional, and AHA coverage", () => {
  const ids = HEART_COMPONENTS.map((component) => component.id);
  assert.equal(new Set(ids).size, ids.length);
  assert.equal(HeartComponentRegistry.getComponentsByCategory("chamber").length, 4);
  assert.equal(HeartComponentRegistry.getComponentsByCategory("valve").length, 4);
  assert.equal(HeartComponentRegistry.getComponentsByCategory("electrical").length, 6);
  assert.equal(HeartComponentRegistry.getComponentsByCategory("functional").length, 6);
  assert.equal(HeartComponentRegistry.getComponentsByCategory("myocardial_segment").length, 17);
  for (let segment = 1; segment <= 17; segment += 1) {
    assert.equal(HeartComponentRegistry.getComponentsForAhaSegment(segment).length, 1);
  }
});

test("registry resolves AHA, territory, finding ID, and normalized LCx mappings", () => {
  assert.deepEqual(HeartComponentRegistry.getComponentsForAhaSegment(1).map(({ id }) => id), ["aha-01"]);
  assert.deepEqual(HeartComponentRegistry.getComponentsForCoronaryTerritory("LAD").map(({ id }) => id), ["lad", "aha-01", "aha-02", "aha-07", "aha-08", "aha-13", "aha-14", "aha-17"]);
  assert.ok(HeartComponentRegistry.getComponentsForFinding({ id: "aha-01" }).some(({ id }) => id === "aha-01"));
  assert.ok(HeartComponentRegistry.getComponentsForFinding({ territory: "lcx" }).some(({ id }) => id === "lcx"));
  assert.equal(HeartComponentRegistry.getComponentsForFinding({ territory: "unknown" }).length, 0);
});

test("selection transitions derive mode and reset transient and persistent state", () => {
  const selected = selectComponent(EMPTY_HEART_SELECTION, "left-ventricle");
  assert.deepEqual(selected, { selectedId: "left-ventricle", hoveredId: null, focusedId: null, mode: "selected" });
  const hovered = hoverComponent(selected, "aorta");
  assert.equal(hovered.mode, "selected");
  assert.equal(clearHover(hovered).hoveredId, null);
  const focused = focusComponent(selected, "left-ventricle");
  assert.equal(focused.mode, "focused");
  assert.equal(clearFocus(focused).mode, "selected");
  assert.deepEqual(resetHeartInteraction(), EMPTY_HEART_SELECTION);
});

test("interaction controller handles ESC, background reset, subscriptions, and invalid IDs", () => {
  const controller = createInteractionController();
  const observed: string[] = [];
  const unsubscribe = controller.subscribe((state) => observed.push(state.mode));
  controller.select("left-ventricle");
  controller.hover("");
  assert.equal(controller.getState().selectedId, "left-ventricle");
  let prevented = false;
  assert.equal(controller.handleEscape({ key: "Enter", preventDefault: () => { prevented = true; } }), false);
  assert.equal(controller.handleEscape({ key: "Escape", preventDefault: () => { prevented = true; } }), true);
  assert.equal(prevented, true);
  assert.deepEqual(controller.getState(), EMPTY_HEART_SELECTION);
  controller.select("aorta");
  controller.handleBackgroundPointerDown();
  assert.deepEqual(controller.getState(), EMPTY_HEART_SELECTION);
  unsubscribe();
  assert.deepEqual(observed, ["selected", "none", "selected", "none"]);
});

test("semantic picking finds parent IDs and terminates on cyclic parents", () => {
  const parent = { userData: { heartComponentId: "aorta" }, parent: null };
  const child = { userData: {}, parent };
  assert.equal(getSemanticComponentId(child), "aorta");
  assert.equal(getSemanticComponentIdFromEvent({ object: child }), "aorta");
  type CycleObject = { userData: unknown; parent: CycleObject | null };
  const cycle: CycleObject = { userData: {}, parent: null };
  cycle.parent = cycle;
  assert.equal(getSemanticComponentId(cycle), null);
});
