# Intended users and use context

## Primary intended user

BeatIT is designed first for a **cardiologist using an educational simulation
in a supervised setting**, such as preparing for or supporting a recovery or
follow-up conversation. The clinician remains responsible for interpreting the
source evidence and for all clinical decisions.

The intended workflow is:

1. select a synthetic, de-identified, or appropriately governed case;
2. review supplied evidence and missing fields;
3. build a deterministic baseline;
4. pose a physiology question;
5. change one or more bounded model parameters;
6. compare the baseline with a hypothetical simulated branch;
7. review assumptions, provenance, descriptive uncertainty, and limitations;
8. use the result, if appropriate, as supervised educational material.

This is the repository's product hypothesis. It has not been validated through
a clinical usability or outcomes study.

## Secondary users

### Cardiovascular researchers

Researchers may use the deterministic engine, seeded plausible-twin ensembles,
paired simulations, and provenance contracts to inspect computational behavior.
BeatIT is not a validated research instrument, and repository test results
should be described as engineering verification rather than clinical evidence.

### Clinical educators and trainees

Educators and trainees may explore how declared model inputs affect calculated
outputs. Simulations must not be presented as patient-specific forecasts,
diagnoses, or treatment effects.

### Imaging and electrophysiology collaborators

Specialists may inspect source-labelled ECG features, procedural anatomy
mapping, or the optional VISTA-3D boundary. The current 3D heart is procedural,
and checkpoint presence or adapter code does not prove live segmentation or
patient-specific geometry.

### Engineers and safety reviewers

Engineers may audit deterministic formulas, scenario bounds, persistence,
provider fallbacks, and safety contracts. Privacy, security, availability, and
multi-user production controls remain deployment responsibilities and are not
established by the local demo.

## Institutional stakeholders

Potential evaluators or future buyers—not current customers—could include:

- academic medical centers and cardiovascular institutes;
- cardiology service lines and supervised cardiac rehabilitation programs;
- research hospitals and cardiovascular modeling groups;
- life-sciences research teams evaluating computational workflows.

Clinical informatics, privacy, security, legal, compliance, and regulatory
teams would need to participate before any patient-data or production use.

## Not an intended user or setting

BeatIT is not intended for:

- unsupervised patient or caregiver decision-making;
- emergency or urgent-care triage;
- diagnosis, prognosis, prescribing, dosing, or treatment selection;
- autonomous clinical decisions;
- validated patient-outcome prediction;
- combining unrelated subjects from different datasets into a synthetic
  “patient” without explicit labeling;
- processing identifiable patient information in the current public-demo or
  local-development configuration.

If a user asks for diagnosis, treatment, medication, or emergency guidance,
BeatIT should decline that task. A disclaimer alone is not sufficient.

## User needs the implementation currently addresses

| User need | Repository support | Qualification |
|---|---|---|
| Reproduce a baseline calculation | Deterministic Python functions and golden/repeatability tests | Engineering evidence only |
| Distinguish evidence from simulation | Source/status models and UI badges | Complete coverage of every displayed value is still an open gate |
| Explore a bounded hypothetical change | Validated scenario parameters and immutable origins | A model response, not a patient forecast |
| Represent uncertain inputs | Seeded plausible-twin ensembles with rejection accounting | Descriptive samples, not a validated posterior |
| Compare like with like | Same-sample Shadow Trial pairing | Not a clinical trial or causal treatment-effect estimate |
| Ask what drives modeled uncertainty | Missing Piece sensitivity/evidence-priority views | Heuristic priority, not advice to order a test |
| Continue without optional AI services | Deterministic fallback behavior | Some language functionality may be degraded or unavailable |

## Evidence needed to advance the user claim

Before describing BeatIT as effective clinical decision support, future work
would need to define and evaluate:

- representative users, tasks, environments, and failure modes;
- comprehension of observed, derived, prior, synthetic, and simulated status;
- whether clinicians can independently review the basis of outputs;
- usability, accessibility, workload, and automation-bias risks;
- performance on governed, representative data;
- calibration and uncertainty communication;
- impact on workflow and patient communication without measuring only
  subjective enthusiasm;
- regulatory status based on the final intended use and functionality.

Relevant guidance and human-factors context:

- US FDA,
  [Applying Human Factors and Usability Engineering to Medical Devices](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/applying-human-factors-and-usability-engineering-medical-devices)
  (2016).
- US FDA,
  [Clinical Decision Support Software](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software)
  (2022).
- World Health Organization,
  [Ethics and governance of artificial intelligence for health](https://www.who.int/publications/i/item/9789240029200)
  (2021).
