import assert from "node:assert/strict";
import test from "node:test";
import { getSuggestedActions } from "@/lib/assistant/suggestedActions";

test("no context returns 2-4 generic starter suggestions", () => {
  const actions = getSuggestedActions({});
  assert.ok(actions.length >= 2 && actions.length <= 4);
});

test("a selected component returns the spec's component suggestion set", () => {
  const actions = getSuggestedActions({ component_id: "LV" });
  assert.deepEqual(
    actions.map((a) => a.label),
    ["Explain this component", "Show evidence", "Compare over time", "Why uncertain?"],
  );
  assert.ok(actions.length >= 2 && actions.length <= 4);
});

test("an open pair returns the spec's compare suggestion set, taking priority over a selected component", () => {
  const actions = getSuggestedActions({ component_id: "LV", pair_id: "284" });
  assert.deepEqual(
    actions.map((a) => a.label),
    ["Explain the difference", "Show causal path", "Inspect PV change"],
  );
  assert.ok(actions.length >= 2 && actions.length <= 4);
});

test("snapshot_id or target_metric alone (no component, no pair) falls back to generic", () => {
  const actions = getSuggestedActions({ snapshot_id: "snap-1", target_metric: "ef" });
  assert.deepEqual(
    actions.map((a) => a.label),
    getSuggestedActions({}).map((a) => a.label),
  );
});

test("every action's label and chat-prompt text stay in sync", () => {
  for (const context of [{}, { component_id: "LV" }, { pair_id: "284" }]) {
    for (const suggestion of getSuggestedActions(context)) {
      assert.equal(typeof suggestion.label, "string");
      assert.equal(typeof suggestion.action, "string");
      assert.ok(suggestion.label.length > 0);
    }
  }
});
