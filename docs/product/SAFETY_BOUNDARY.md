# Safety and product boundary

## Current intended use

BeatIT is an **educational and research cardiovascular simulation** for
clinician-supervised exploration and communication. It organizes supplied
evidence, computes a reproducible modeled baseline, runs bounded hypothetical
scenarios, and exposes assumptions and limitations.

BeatIT is not clinically validated, cleared, approved, or authorized as a
medical device. Nothing in the repository establishes safety or effectiveness
for clinical use.

## Unsupported uses

BeatIT must not be used for:

- diagnosis or exclusion of disease;
- prognosis or patient-outcome prediction;
- treatment, medication, device, or procedure selection;
- prescribing or dose adjustment;
- emergency screening, triage, or time-critical guidance;
- autonomous care decisions;
- replacing review of source records or licensed professional judgment;
- representing simulated deltas as benefit, harm, efficacy, or treatment
  effect.

“Shadow Trial” is BeatIT's name for paired computational counterfactual
simulation. It is not a clinical trial. “Missing Piece” ranks modeled
sensitivity and evidence priority; it does not advise a clinician to order a
test.

## Authority boundary

| Capability | Permitted role | Prohibited interpretation |
|---|---|---|
| Deterministic cardiac engine | Calculate versioned model outputs from explicit inputs | Clinically validated truth or individualized prediction |
| Plausible-twin ensemble | Describe outputs across accepted, bounded input samples | Patient probability, confidence interval, or validated posterior |
| Scenario engine | Propagate a hypothetical parameter change | Treatment recommendation or causal clinical effect |
| Language model | Extract, route, summarize, or explain tool-established facts | Invent or overwrite canonical physiology |
| VISTA-3D adapter | Return optional segmentation artifacts when configured | Proof of diagnosis, chamber-level accuracy, or live availability |
| Procedural 3D heart | Visualize model state and interaction | Patient-specific anatomy or scan reconstruction |

The observed/source-backed snapshot must remain distinct from hypothetical
states. Priors must not be relabeled as observations. Missing provider output
must remain unavailable rather than being fabricated.

## Implemented safeguards

The repository includes:

- canonical disclaimers in API and product surfaces;
- request and generated-language checks for prohibited diagnostic, treatment,
  medication, and emergency-authority language;
- deterministic numerical tools separated from optional language providers;
- bounded scenario validation and immutable scenario origins;
- explicit statuses including observed, derived, simulated, prior, and
  synthetic;
- rejected-sample accounting rather than silent clamping in the ensemble path;
- optional-service fallbacks for language and VISTA integrations;
- report sections that can remain visibly unavailable;
- focused safety and contract tests.

These are risk controls, not proof of clinical safety. Repository reviews note
that safety coverage is not complete on every public/error surface and that
provenance coverage remains an open release gate.

## Required communication rules

Use:

- “bounded hypothetical simulation”;
- “modeled or simulated trajectory”;
- “descriptive sampled spread”;
- “local sensitivity” or “evidence-priority heuristic”;
- “engineering verification and reproducibility”;
- “procedural cardiac visualization.”

Do not use:

- “predicted patient outcome”;
- “recommended treatment”;
- “clinical confidence interval” unless a validated interval exists;
- “clinical trial” for a Shadow Trial;
- “clinical validation” for tests or golden fixtures;
- “patient-specific anatomy” for procedural geometry.

## Data, privacy, and deployment boundary

The current repository does not establish a production environment suitable
for identifiable health information. Before such use, a deployment would need
an organization-specific assessment covering at least access control, tenant
isolation, encryption, audit logging, retention and deletion, backups,
incident response, vendor agreements, consent and data-use terms, and
jurisdictional requirements.

HIPAA applicability depends on the entities, data, and activities involved;
technology alone is not “HIPAA compliant.” Relevant US sources include:

- [HHS: HIPAA Privacy Rule](https://www.hhs.gov/hipaa/for-professionals/privacy/index.html)
- [HHS: HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [HHS: Guidance Regarding Methods for De-identification of Protected Health Information](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html)

Only synthetic, de-identified, public, or appropriately governed data may be
used, consistent with license and data-use restrictions. Missing modalities
must remain missing. Records from unrelated subjects must not be joined and
presented as one person.

## Regulatory boundary

Regulatory status depends on intended use, claims, functionality, users, and
deployment context. The FDA's clinical decision support guidance discusses,
among other factors, whether software provides recommendations and whether a
health-care professional can independently review their basis. BeatIT's
inspectability is relevant to that question but does not itself determine that
BeatIT is outside device regulation.

- US FDA,
  [Clinical Decision Support Software: Guidance for Industry and FDA Staff](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software)
  (2022).
- US FDA,
  [Software as a Medical Device (SaMD)](https://www.fda.gov/medical-devices/digital-health-center-excellence/software-medical-device-samd)
- International Medical Device Regulators Forum,
  [Software as a Medical Device: Clinical Evaluation](https://www.imdrf.org/documents/software-medical-device-samd-clinical-evaluation)
  (2017).

A qualified regulatory assessment is required before changing claims or
intended use.

## Failure behavior

When evidence or an optional provider is unavailable, BeatIT should:

1. preserve deterministic core functionality where possible;
2. identify the unavailable capability;
3. avoid filling the gap with generated facts;
4. retain the safety disclaimer and epistemic status;
5. reject prohibited requests explicitly;
6. fail closed for authentication or data-access uncertainty.

For emergency requests, BeatIT must not attempt triage. A production product
would need a jurisdiction-appropriate, reviewed escalation design; the current
simulation should direct the user away from relying on BeatIT for urgent help.

## Conditions for revisiting this boundary

Any move toward diagnosis, prognosis, treatment comparison, patient-specific
recommendations, unsupervised patient use, or real-time clinical monitoring is
a material change. It requires new hazard analysis, clinical and analytical
evidence, human-factors work, privacy/security controls, quality processes, and
regulatory review. Existing tests and disclaimers cannot authorize that change.
