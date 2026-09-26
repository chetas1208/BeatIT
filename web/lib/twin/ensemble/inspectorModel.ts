import type { EnsembleMetricId, OutputDistribution, TwinEnsemble } from "@/lib/twin/ensemble/contracts";
import { HeartComponentRegistry } from "@/lib/heart/registry";
import type { TwinEventSource } from "@/lib/twin/time/contracts";

const COMPONENT_METRICS: Readonly<Record<string, readonly string[]>> = {
  "left-ventricle": ["ejection_fraction_pct", "stroke_volume_ml", "cardiac_output_l_min"],
  "blood-flow": ["stroke_volume_ml", "cardiac_output_l_min"],
};

const METRIC_LABELS: Readonly<Record<EnsembleMetricId, string>> = {
  ejection_fraction_pct: "Ejection fraction",
  stroke_volume_ml: "Stroke volume",
  cardiac_output_l_min: "Cardiac output",
  heart_rate_bpm: "Heart rate",
};

const ORIGIN_QUALITY_LABELS = {
  observed: "Observed",
  derived: "Derived",
  interpolated: "Interpolated",
  synthetic: "Synthetic replay",
} as const;

const PROVENANCE_SOURCE_LABELS: Readonly<Record<TwinEventSource, string>> = {
  clinical_record: "Clinical record",
  imaging: "Imaging",
  ecg: "ECG",
  wearable: "Wearable",
  synthetic_replay: "Synthetic replay",
  user_annotation: "User annotation",
  derived_model: "Derived model",
};

export interface ComponentUncertaintyView {
  readonly componentLabel: string;
  readonly distributions: readonly OutputDistribution[];
  readonly unavailableMessage: string;
  readonly originQualityLabel: string;
  readonly provenanceSourceLabel: string;
}

export function metricLabel(metricId: string): string {
  if (metricId in METRIC_LABELS) return METRIC_LABELS[metricId as EnsembleMetricId];
  return metricId.replaceAll("_", " ");
}

export function getComponentUncertaintyView(
  ensemble: TwinEnsemble,
  componentId = "left-ventricle",
): ComponentUncertaintyView {
  const componentLabel = HeartComponentRegistry.getComponent(componentId)?.displayName ?? "Selected component";
  const metricIds = COMPONENT_METRICS[componentId] ?? [];
  const distributions = ensemble.distributions.filter((distribution) => metricIds.includes(distribution.metricId));
  const provenanceSources = [...new Set(ensemble.provenance.originProvenance.map((item) => PROVENANCE_SOURCE_LABELS[item.source] ?? "Unrecognized source"))];

  return {
    componentLabel,
    distributions,
    unavailableMessage: `Component-specific scalar uncertainty is unavailable for ${componentLabel}. No anatomical uncertainty is inferred.`,
    originQualityLabel: ORIGIN_QUALITY_LABELS[ensemble.provenance.originQuality],
    provenanceSourceLabel: provenanceSources.length > 0 ? provenanceSources.join(", ") : "Unavailable",
  };
}
