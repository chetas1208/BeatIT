import assert from "node:assert/strict";
import test from "node:test";
import { summarizeDistribution } from "@/lib/twin/ensemble/statistics";

test("calculates mean, median, population variance, and standard deviation", () => {
  const summary = summarizeDistribution("heart_rate_bpm", "bpm", [1, 2, 3, 4]);

  assert.equal(summary.mean, 2.5);
  assert.equal(summary.median, 2.5);
  assert.equal(summary.variance, 1.25);
  assert.equal(summary.standardDeviation, Math.sqrt(1.25));
});

test("sorts samples in the summary without mutating the input", () => {
  const values = [4, 1, 3, 2];
  const summary = summarizeDistribution("metric", "unit", values);

  assert.deepEqual(summary.samples, [1, 2, 3, 4]);
  assert.deepEqual(values, [4, 1, 3, 2]);
  assert.equal(summary.min, 1);
  assert.equal(summary.max, 4);
});

test("interpolates the configured quantiles", () => {
  const summary = summarizeDistribution("metric", "unit", [40, 0, 30, 10, 20]);

  assert.deepEqual(summary.quantiles, { q05: 2, q25: 10, q75: 30, q95: 38 });
});

test("rejects empty and non-finite samples", () => {
  const invalidSamples: readonly number[][] = [[], [Number.NaN], [Number.POSITIVE_INFINITY], [Number.NEGATIVE_INFINITY]];

  for (const values of invalidSamples) {
    assert.throws(
      () => summarizeDistribution("metric", "unit", values),
      (error: unknown) => error instanceof RangeError && error.message === "Statistics require finite samples",
    );
  }
});

test("handles a single sample without introducing variance or quantile error", () => {
  const summary = summarizeDistribution("metric", "unit", [7]);

  assert.equal(summary.mean, 7);
  assert.equal(summary.median, 7);
  assert.equal(summary.variance, 0);
  assert.equal(summary.standardDeviation, 0);
  assert.deepEqual(summary.quantiles, { q05: 7, q25: 7, q75: 7, q95: 7 });
  assert.equal(summary.min, 7);
  assert.equal(summary.max, 7);
});

test("interpolates quantiles correctly for two samples", () => {
  const summary = summarizeDistribution("metric", "unit", [6, 2]);

  assert.equal(summary.mean, 4);
  assert.equal(summary.median, 4);
  assert.equal(summary.variance, 4);
  assert.deepEqual(summary.quantiles, { q05: 2.2, q25: 3, q75: 5, q95: 5.8 });
});
