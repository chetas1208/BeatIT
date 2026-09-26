import assert from "node:assert/strict";
import test from "node:test";
import { nextTrapFocusTarget } from "@/lib/assistant/useFocusTrap";

// nextTrapFocusTarget only ever compares elements by identity (===) and reads
// .length / indexOf, so plain objects stand in for HTMLElements here — no DOM
// (jsdom/testing-library) is set up in this repo's test runner.
function fakeElements(count: number) {
  return Array.from({ length: count }, () => ({})) as unknown as HTMLElement[];
}

test("nextTrapFocusTarget: empty list returns null", () => {
  assert.equal(nextTrapFocusTarget([], null, false), null);
});

test("forward tab from the last element wraps to the first", () => {
  const [first, , last] = fakeElements(3);
  const list = [first, fakeElements(1)[0], last];
  assert.equal(nextTrapFocusTarget(list, list[2], false), list[0]);
});

test("forward tab from a middle element defers to default browser behavior", () => {
  const list = fakeElements(3);
  assert.equal(nextTrapFocusTarget(list, list[1], false), null);
});

test("forward tab with no active element (focus left the trap) goes to first", () => {
  const list = fakeElements(3);
  assert.equal(nextTrapFocusTarget(list, null, false), list[0]);
});

test("shift+tab from the first element wraps to the last", () => {
  const list = fakeElements(3);
  assert.equal(nextTrapFocusTarget(list, list[0], true), list[list.length - 1]);
});

test("shift+tab from a middle element defers to default browser behavior", () => {
  const list = fakeElements(3);
  assert.equal(nextTrapFocusTarget(list, list[1], true), null);
});

test("single focusable element: forward tab re-focuses it (stays trapped)", () => {
  const list = fakeElements(1);
  assert.equal(nextTrapFocusTarget(list, list[0], false), list[0]);
  assert.equal(nextTrapFocusTarget(list, list[0], true), list[0]);
});
