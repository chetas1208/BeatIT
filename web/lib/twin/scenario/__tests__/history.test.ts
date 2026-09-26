import assert from "node:assert/strict";
import test from "node:test";
import {
  createScenarioHistory,
  pushScenario,
  redoScenario,
  resetScenario,
  undoScenario,
} from "@/lib/twin/scenario/history";
import type { ScenarioResult } from "@/lib/twin/scenario/types";

function scenario(id: string): ScenarioResult {
  return { id } as unknown as ScenarioResult;
}

test("push stores the present result and clears the redo branch", () => {
  const first = scenario("first");
  const second = scenario("second");
  const replacement = scenario("replacement");

  const initial = createScenarioHistory();
  const withFirst = pushScenario(initial, first);
  const withSecond = pushScenario(withFirst, second);
  const afterUndo = undoScenario(withSecond);
  const afterReplacement = pushScenario(afterUndo, replacement);

  assert.deepEqual(afterReplacement, {
    past: [first, second],
    present: replacement,
    future: [],
  });
  assert.deepEqual(withSecond, { past: [first], present: second, future: [] });
});

test("undo and redo move results between past, present, and future", () => {
  const first = scenario("first");
  const second = scenario("second");
  const third = scenario("third");
  const initial = createScenarioHistory();
  const history = pushScenario(pushScenario(pushScenario(initial, first), second), third);

  const afterUndo = undoScenario(history);
  assert.deepEqual(afterUndo, { past: [first], present: second, future: [third] });

  const afterSecondUndo = undoScenario(afterUndo);
  assert.deepEqual(afterSecondUndo, { past: [], present: first, future: [second, third] });

  const afterRedo = redoScenario(afterSecondUndo);
  assert.deepEqual(afterRedo, { past: [first], present: second, future: [third] });
  assert.equal(undoScenario(initial), initial);
  assert.equal(redoScenario(initial), initial);
});

test("reset clears the present result and both history stacks", () => {
  const first = scenario("first");
  const second = scenario("second");
  const history = undoScenario(pushScenario(pushScenario(createScenarioHistory(), first), second));

  assert.deepEqual(resetScenario(history), { past: [], present: null, future: [] });
});
