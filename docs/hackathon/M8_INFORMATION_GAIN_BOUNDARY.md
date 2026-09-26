# M8 Information-Gain Boundary

Status: **Tier-1 boundary**  
Date: 2026-09-26

## What M8 computes

M8 computes only transparent deterministic research projections:

1. local finite-difference sensitivity of a selected canonical output or M6
   paired effect to one bounded model parameter; and
2. an **uncertainty-impact heuristic**, formed from sampled parameter spread
   and the magnitude of the local response.

Evidence ranking is an **Evidence Priority Score**. It applies an explicit,
versioned evidence-to-parameter map and reviewed strength weights to the
uncertainty-impact scores. The score is a deterministic prioritization aid,
not a probability or a measurement-outcome prediction.

The word *heuristic* is required. The expression `sensitivity × uncertainty`
is never relabeled as expected information gain, information gain, value of
information, expected value of sample information, entropy reduction, mutual
information, a posterior update, or a variance decomposition.

## What M8 does not compute

M8 does not calculate, estimate, or approximate any of the following:

- expected information gain or information gain for a candidate observation;
- entropy, differential entropy, mutual information, KL divergence, or any
  other distributional information quantity;
- expected value of information, expected value of sample information, or a
  measurement-cost-adjusted utility;
- a likelihood, posterior distribution, Bayesian update, or probability that a
  candidate observation will change a parameter or ranking;
- a confidence interval, credible interval, variance share, Sobol index,
  Morris index, Shapley attribution, or other global uncertainty statistic;
- a calibrated probability that evidence will reduce uncertainty, improve a
  target metric, alter an M6 effect, or help an individual;
- a diagnostic, treatment, emergency, or measurement recommendation.

The Evidence Priority Score is therefore not a claim that a proposed
measurement is more informative in the statistical sense. It is not a
guarantee that collecting evidence will reduce uncertainty, resolve a model
ambiguity, improve an outcome, or benefit a patient.

## Required prerequisites for future actual IG

A future implementation may use information-gain terminology only after all
of the following are defined, versioned, validated, and exposed in its result
provenance:

1. **Candidate observation space:** the observable, target, units, timing,
   sampling process, missingness rules, and admissible evidence conditions.
2. **Observation model:** a likelihood or equivalent generative model
   `p(observation | parameters, candidate evidence)`, including measurement
   noise, bias, limits of detection, missingness, and selection effects where
   relevant.
3. **Joint uncertainty model:** a normalized prior or current joint
   distribution over parameters, including correlations, support, and how the
   distribution was obtained from M5.5 data. Independent marginals are not
   sufficient when correlations affect the result.
4. **Update rule:** a specified posterior or other update operation that maps
   each possible observation to updated uncertainty, with numerical handling
   for invalid, censored, or out-of-support observations.
5. **Quantity and utility:** an exact definition of the reported information
   quantity, its target metric, and—if the claim is value rather than
   information—a utility/loss function and measurement cost.
6. **Numerical procedure:** a deterministic, tested integration or sampling
   procedure, convergence/error checks, seed/version recording, and behavior
   for degenerate or unavailable distributions.
7. **Empirical validation:** calibration and held-out validation of the
   observation model and update behavior against appropriate real or
   explicitly synthetic observations, plus sensitivity analysis for modeling
   assumptions.

Until these gates exist, a result may be called only an
`uncertainty-impact heuristic`, `Evidence Priority Score`, local sensitivity,
or another explicitly descriptive quantity whose computation is documented.
The UI, API, schemas, tests, and narrative must preserve that boundary and
must not imply that a ranked item has an expected information value.

All outputs remain educational deterministic research projections and retain
the canonical BeatIT safety disclaimer.
