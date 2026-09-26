import type { OutputDistribution, TwinEnsemble } from "@/lib/twin/ensemble/contracts";

export interface PVUncertaintyEnvelope {
  mode: "scalar_pv_linked";
  ejectionFraction: OutputDistribution | null;
  strokeVolume: OutputDistribution | null;
  pointwiseLoopAvailable: false;
  limitation: string;
}

/**
 * Build the honest PV-linked uncertainty surface from backend summaries.
 * Pointwise loop samples are not part of the current API contract, so this
 * function never fabricates a curve envelope from scalar percentiles.
 */
export function pvUncertaintyEnvelope(ensemble: TwinEnsemble): PVUncertaintyEnvelope {
  return {
    mode: "scalar_pv_linked",
    ejectionFraction: ensemble.distributions.find((item) => item.metricId === "ejection_fraction_pct") ?? null,
    strokeVolume: ensemble.distributions.find((item) => item.metricId === "stroke_volume_ml") ?? null,
    pointwiseLoopAvailable: false,
    limitation: "Backend returned scalar EF and stroke-volume uncertainty; pointwise PV loop uncertainty is not available.",
  };
}
