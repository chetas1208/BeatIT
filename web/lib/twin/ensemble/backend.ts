import { createTwinEnsemble } from "@/lib/api";
import type { ParameterDistribution, TwinEnsemble } from "@/lib/twin/ensemble/contracts";
import { mapBackendEnsembleResponse } from "@/lib/twin/ensemble/adapter";
import { baselineScenarioParameters } from "@/lib/twin/scenario/propagation";
import { getScenarioParameterDefinition, type ScenarioParameterKey } from "@/lib/twin/scenario/parameters";
import type { TwinSnapshot } from "@/lib/twin/time/contracts";
import type { EnsembleApiRequestDistribution } from "@/types/ensemble";

const PHYSIOLOGY_VERSION = "m5.5-ensemble-projection-v1";
const DISTRIBUTION_VERSION = "m5.5-backend-ensemble-v1";
const PRIOR_VERSION = "m5-priors-v1";

/** Build only the input distribution request; the backend samples and evaluates it. */
export function defaultBackendDistributions(snapshot: TwinSnapshot): ParameterDistribution[] {
  const values = baselineScenarioParameters(snapshot);
  const definitions = [
    ["heart_rate_bpm", 3, "Heart rate measurement-scale uncertainty."],
    ["preload_index", 0.08, "Preload is a bounded proxy informed by EDV."],
    ["afterload_index", 0.1, "Afterload is a bounded proxy, not a direct blood-pressure measurement."],
    ["contractility_index", 0.12, "Contractility is a bounded proxy informed directionally by EF."],
    ["systemic_vascular_resistance_index", 0.12, "SVR is a bounded proxy with an explicit prior."],
  ] as const;
  return definitions.map(([parameterId, sd, rationale]) => {
    const key = parameterId as ScenarioParameterKey;
    const definition = getScenarioParameterDefinition(key)!;
    const boundedMean = Math.min(definition.max, Math.max(definition.min, values[key]));
    return {
      parameterId: key,
      family: "normal",
      parameters: { mean: boundedMean, sd },
      bounds: { min: definition.min, max: definition.max },
      source: "derived",
      evidenceIds: [],
      rationale,
      version: PRIOR_VERSION,
    } satisfies ParameterDistribution;
  });
}

function toApiDistribution(distribution: ParameterDistribution): EnsembleApiRequestDistribution {
  return {
    parameter_id: distribution.parameterId,
    family: distribution.family,
    parameters: Object.fromEntries(Object.entries(distribution.parameters).map(([key, value]) => [key, Array.isArray(value) ? Array.from(value) : value])) as Record<string, number | number[]>,
    bounds: { ...distribution.bounds },
    source: distribution.source,
    evidence_ids: [...distribution.evidenceIds],
    rationale: distribution.rationale,
    version: distribution.version,
  };
}

export async function generateBackendEnsemble(snapshot: TwinSnapshot, sampleCount: number, seed: number): Promise<TwinEnsemble> {
  const distributions = defaultBackendDistributions(snapshot);
  const response = await createTwinEnsemble({
    origin_snapshot_id: snapshot.id,
    state: snapshot.state,
    seed,
    sample_count: sampleCount,
    distributions: distributions.map(toApiDistribution),
    physiology_version: PHYSIOLOGY_VERSION,
    distribution_config_version: DISTRIBUTION_VERSION,
    prior_version: PRIOR_VERSION,
    origin_quality: snapshot.quality,
    origin_provenance: snapshot.provenance,
    evidence_ids: snapshot.evidenceIds,
  });
  return mapBackendEnsembleResponse(response);
}

export const ensembleContractVersions = {
  physiology: PHYSIOLOGY_VERSION,
  distribution: DISTRIBUTION_VERSION,
  prior: PRIOR_VERSION,
} as const;
