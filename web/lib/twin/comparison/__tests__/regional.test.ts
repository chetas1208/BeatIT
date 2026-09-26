import assert from "node:assert/strict";
import test from "node:test";
import {
  buildRegionalDifference,
  buildRegionalDifferences,
  type ExplicitRegionalDelta,
} from "@/lib/twin/comparison/regional";
import type { CardiacFinding } from "@/types/heart";

function finding(
  id: string,
  segments: number[],
  overrides: Partial<CardiacFinding> = {},
): CardiacFinding {
  return {
    id,
    title: "Regional finding",
    region: "Anterior wall",
    territory: "LAD",
    aha_segments: segments,
    anchor: { x: 0, y: 0, z: 0 },
    severity: "moderate",
    summary: "Explicit educational simulation finding.",
    metric: "scar fraction 0.20",
    codes: [{ system: "AHA 17-segment model", code: "1,7,13", label: "Anterior wall segments" }],
    source: "state.tissue_state.damage_zone_location + scar_fraction",
    ...overrides,
  };
}

const explicitDelta: ExplicitRegionalDelta = {
  value: 0.05,
  unit: "scar fraction",
  source: "paired regional finding evidence",
  evidence: ["Scenario finding explicitly reports scar fraction change."],
};

test("maps a paired explicit regional finding and preserves supplied delta evidence", () => {
  const result = buildRegionalDifference(
    finding("regional_anterior", [13, 1, 7]),
    finding("regional_anterior", [1, 7, 13]),
    explicitDelta,
  );

  assert.equal(result.findingId, "regional_anterior");
  assert.equal(result.mappingAvailability, "available");
  assert.equal(result.deltaAvailability, "available");
  assert.deepEqual(result.ahaSegments, [1, 7, 13]);
  assert.deepEqual(result.delta, explicitDelta);
  assert.match(result.evidence.join(" "), /Baseline finding regional_anterior/);
  assert.match(result.evidence.join(" "), /Scenario finding explicitly reports/);
});

test("keeps the AHA mapping but marks the regional delta unavailable when none is explicit", () => {
  const result = buildRegionalDifference(
    finding("regional_inferior", [4, 10, 15]),
    finding("regional_inferior", [4, 10, 15]),
  );

  assert.equal(result.mappingAvailability, "available");
  assert.equal(result.deltaAvailability, "unavailable");
  assert.equal(result.delta, null);
  assert.match(result.limitation, /scalar differences are not localized/);
});

test("fails closed for missing, mismatched, malformed, and non-regional findings", () => {
  const missingScenario = buildRegionalDifference(finding("regional_lateral", [5, 6, 11, 12, 16]), null);
  const mismatchedId = buildRegionalDifference(
    finding("regional_anterior", [1, 7, 13]),
    finding("regional_inferior", [4, 10, 15]),
  );
  const mismatchedSegments = buildRegionalDifference(
    finding("regional_anterior", [1, 7, 13]),
    finding("regional_anterior", [1, 7]),
  );
  const mismatchedRegion = buildRegionalDifference(
    finding("regional_anterior", [1, 7, 13]),
    finding("regional_anterior", [1, 7, 13], { region: "Inferior wall" }),
  );
  const malformed = buildRegionalDifference(
    finding("regional_anterior", [1, 7, 13], { aha_segments: [1, 18] }),
    finding("regional_anterior", [1, 7, 13]),
  );
  const global = buildRegionalDifference(
    finding("global_systolic", [1, 2, 3]),
    finding("global_systolic", [1, 2, 3]),
  );

  for (const result of [missingScenario, mismatchedId, mismatchedSegments, mismatchedRegion, malformed, global]) {
    assert.equal(result.mappingAvailability, "unavailable");
    assert.equal(result.deltaAvailability, "unavailable");
    assert.deepEqual(result.ahaSegments, []);
    assert.equal(result.delta, null);
  }
  assert.match(missingScenario.limitation, /paired explicit finding evidence/);
  assert.match(mismatchedRegion.evidence.join(" "), /different regional labels/);
});

test("builds stable union rows and rejects duplicate IDs without choosing a winner", () => {
  const results = buildRegionalDifferences({
    baselineFindings: [finding("regional_z", [5, 11]), finding("regional_z", [5, 11])],
    scenarioFindings: [finding("regional_a", [1, 7, 13])],
    explicitDeltas: { regional_a: explicitDelta },
  });

  assert.deepEqual(results.map((result) => result.findingId), ["regional_a", "regional_z"]);
  assert.equal(results[0]?.mappingAvailability, "unavailable");
  assert.equal(results[1]?.mappingAvailability, "unavailable");
  assert.match(results[1]?.evidence.join(" ") ?? "", /ambiguous/);
});

test("does not treat a malformed explicit delta as zero or as a regional delta", () => {
  const result = buildRegionalDifference(
    finding("regional_anterior", [1, 7, 13]),
    finding("regional_anterior", [1, 7, 13]),
    { ...explicitDelta, value: Number.NaN, evidence: [" "] },
  );

  assert.equal(result.mappingAvailability, "available");
  assert.equal(result.deltaAvailability, "unavailable");
  assert.equal(result.delta, null);
});
