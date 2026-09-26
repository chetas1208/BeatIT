import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { shouldApplyMissingPieceResult } from "../requestIdentity";

describe("shouldApplyMissingPieceResult", () => {
  it("accepts matching token and selection", () => {
    assert.equal(
      shouldApplyMissingPieceResult(
        2,
        2,
        { ensembleId: "ens-1", metric: "stroke_volume_ml" },
        { ensembleId: "ens-1", metric: "stroke_volume_ml" },
      ),
      true,
    );
  });

  it("rejects stale token", () => {
    assert.equal(
      shouldApplyMissingPieceResult(
        1,
        2,
        { ensembleId: "ens-1", metric: "stroke_volume_ml" },
        { ensembleId: "ens-1", metric: "stroke_volume_ml" },
      ),
      false,
    );
  });

  it("rejects ensemble or metric drift", () => {
    assert.equal(
      shouldApplyMissingPieceResult(
        2,
        2,
        { ensembleId: "ens-1", metric: "stroke_volume_ml" },
        { ensembleId: "ens-2", metric: "stroke_volume_ml" },
      ),
      false,
    );
    assert.equal(
      shouldApplyMissingPieceResult(
        2,
        2,
        { ensembleId: "ens-1", metric: "stroke_volume_ml" },
        { ensembleId: "ens-1", metric: "ejection_fraction_pct" },
      ),
      false,
    );
  });
});
