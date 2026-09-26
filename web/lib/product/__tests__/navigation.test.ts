import assert from "node:assert/strict";
import test from "node:test";
import { modeFromPathname, pathForMode } from "@/lib/product/navigation";

test("maps only the five product paths and fails closed to Twin", () => {
  assert.equal(modeFromPathname("/twin"), "twin");
  assert.equal(modeFromPathname("/experiment"), "experiment");
  assert.equal(modeFromPathname("/compare"), "compare");
  assert.equal(modeFromPathname("/evidence"), "evidence");
  assert.equal(modeFromPathname("/report"), "report");
  assert.equal(modeFromPathname("/careguard/runner"), "twin");
  assert.equal(pathForMode("report"), "/report");
});
