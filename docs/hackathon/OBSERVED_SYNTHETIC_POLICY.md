# Observed and synthetic lineage policy

BeatIT distinguishes the origin of a snapshot from the certainty of a
simulation. A plausible twin is always a deterministic simulation over sampled
input proxies; it is never patient evidence and never a diagnosis or treatment
recommendation.

## Required lineage

Every datum is classified by what it represents. The classifications are not
interchangeable:

- `OBSERVED`: a value directly present in an input record or measurement; it
  retains source and evidence identifiers.
- `DERIVED`: a deterministic calculation from observed or otherwise classified
  inputs; it is not a second observation.
- `SIMULATED`: a value produced by the deterministic physiology engine for a
  plausible twin or scenario; it is never patient evidence.
- `SYNTHETIC`: a replay or generated input fixture; it must remain visibly
  synthetic even when its shape resembles an observed record.
- `INTERPOLATED`: a value filled between known observations by the timeline
  model; it is not directly observed.
- `PRIOR`: a bounded model assumption used when evidence is missing; it is not
  an estimate of an individual patient.

At the ensemble request boundary, `origin_quality` uses the input lineage
values `observed`, `derived`, `interpolated`, or `synthetic`. The response
provenance carries that origin, while every accepted sample is classified as
`SIMULATED` by the UI and its projected state values carry `DERIVED` source
metadata. Distribution `source` and `version` fields identify `PRIOR`,
measurement, derived, or scenario inputs without relabeling the output.

The backend preserves this value in the response provenance and every sample.
The frontend displays `PLAUSIBLE SIMULATED TWIN` for every selected sample and
adds `synthetic replay origin` when the origin is synthetic. A synthetic origin
must never be rendered as `LIVE` or described as patient evidence.

## Enforcement boundaries

- `origin_quality` is required at the ensemble API boundary; it is not silently
  defaulted to `observed`.
- The backend remains the authority for sampling, validity, physiology output,
  and descriptive percentiles.
- Percentiles describe accepted deterministic simulations only. They are not
  clinical confidence intervals, credible intervals, likelihoods, or patient
  probabilities.
- Missing or invalid lineage is rejected by the request contract rather than
  repaired in the UI.
- Replayed or synthetic snapshots remain educational fixtures and must carry
  their source provenance when they are promoted to a request.

## Review checklist

Before a demo or release, verify the API payload, response provenance, selected
twin badge, timeline label, and report language agree on the same lineage. If a
surface cannot preserve that distinction, it is not eligible to present an
ensemble result.
