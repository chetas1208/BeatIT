import type { ParameterDistribution, TwinEnsemble, TwinSample } from "@/lib/twin/ensemble/contracts";
import type { ScenarioParameterKey } from "@/lib/twin/scenario/parameters";
import type { EnsembleApiResponse } from "@/types/ensemble";

/** Map the versioned backend wire contract without recalculating any metric. */
export function mapBackendEnsembleResponse(response: EnsembleApiResponse): TwinEnsemble {
  return {
    id: response.id,
    originSnapshotId: response.origin_snapshot_id,
    seed: response.seed,
    requestedSampleCount: response.requested_sample_count,
    acceptedSampleCount: response.accepted_sample_count,
    rejectedSampleCount: response.rejected_sample_count,
    samples: response.samples.map((sample) => ({
      id: sample.id,
      index: sample.index,
      seed: sample.seed,
      originSnapshotId: sample.origin_snapshot_id,
      originQuality: sample.origin_quality,
      parameters: sample.parameters as TwinSample["parameters"],
      state: sample.state,
      valid: sample.valid,
      rejectionReasons: sample.rejection_reasons,
    })),
    distributions: response.distributions.map((distribution) => ({
      metricId: distribution.metric_id,
      unit: distribution.unit,
      samples: distribution.samples,
      mean: distribution.mean,
      median: distribution.median,
      variance: distribution.variance,
      standardDeviation: distribution.standard_deviation,
      quantiles: distribution.quantiles,
      min: distribution.min,
      max: distribution.max,
    })),
    parameterDistributions: response.parameter_distributions.map((distribution) => ({
      parameterId: distribution.parameter_id as ScenarioParameterKey,
      family: distribution.family,
      parameters: distribution.parameters,
      bounds: distribution.bounds,
      source: distribution.source,
      evidenceIds: distribution.evidence_ids,
      rationale: distribution.rationale,
      version: distribution.version,
    } satisfies ParameterDistribution)),
    provenance: {
      originSnapshotId: response.provenance.origin_snapshot_id,
      originTimestamp: response.provenance.origin_timestamp,
      originQuality: response.provenance.origin_quality,
      originProvenance: response.provenance.origin_provenance as TwinEnsemble["provenance"]["originProvenance"],
      parentScenarioId: response.provenance.parent_scenario_id ?? undefined,
      evidenceIds: response.provenance.evidence_ids,
      seed: response.provenance.seed,
      physiologyVersion: response.provenance.physiology_version,
      distributionConfigVersion: response.provenance.distribution_config_version,
      priorVersion: response.provenance.prior_version,
      createdAt: response.provenance.created_at,
      assumptions: response.provenance.assumptions,
    },
    warnings: response.warnings,
    safetyDisclaimer: response.safety_disclaimer,
    representativeIds: response.representative_sample_ids,
  };
}
