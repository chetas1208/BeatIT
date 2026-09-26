import assert from "node:assert/strict";
import test from "node:test";
import { DEFAULT_PRODUCT_CONTEXT } from "@/lib/product/contracts";
import { buildProductReport } from "@/lib/product/reportContracts";

test("report preserves unavailable sections instead of fabricating values", () => {
  const report = buildProductReport({
    context: DEFAULT_PRODUCT_CONTEXT,
    safetyDisclaimer: null,
    hasState: false,
    hasVisualization: false,
    hasTimeline: false,
    hasExperiment: false,
    hasComparison: false,
    hasEvidence: false,
    provenance: [],
  });
  assert.equal(report.sections.every((section) => section.status === "unavailable"), true);
  assert.match(report.safetyDisclaimer, /Educational simulation/);
  assert.equal(report.limitations.length, 3);
});

test("report marks only supplied computational sections ready", () => {
  const report = buildProductReport({
    context: { ...DEFAULT_PRODUCT_CONTEXT, caseId: "case-1" },
    safetyDisclaimer: "Use for education.",
    hasState: true,
    hasVisualization: true,
    hasTimeline: true,
    hasExperiment: false,
    hasComparison: false,
    hasEvidence: true,
    provenance: ["snapshot-1"],
  });
  assert.deepEqual(report.sections.filter((section) => section.status === "ready").map((section) => section.id), ["twin", "timeline", "evidence"]);
  assert.deepEqual(report.sections.find((section) => section.id === "twin")?.provenance, ["snapshot-1"]);
});
