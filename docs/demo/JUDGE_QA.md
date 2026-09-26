# Judge Q&A

## Who is the primary user?

A cardiologist preparing for or conducting a supervised recovery or follow-up
conversation. Secondary users include cardiac rehabilitation educators,
trainees, and researchers.

## What painful workflow does it improve?

Clinicians currently reconcile measurements, reports, assumptions, and
physiology explanations across disconnected tools. BeatIT creates one
inspectable baseline-to-scenario comparison for supervised education.

## Who pays?

The initial buyer hypothesis is a cardiac rehabilitation program, cardiology
service line, or clinical education organization. This must be tested through
workflow pilots and buyer interviews.

## Why would they adopt it?

The hypothesis is reduced preparation/explanation burden and clearer,
reproducible patient education. A pilot should measure time, comprehension, and
safe workflow completion. We do not yet claim proven clinical or economic
benefit.

## What does it replace?

Initially, it consolidates manual explanation work spread across reports,
calculators, diagrams, and ad hoc educational materials. It does not replace
clinical judgment or a diagnostic system.

## Is it decision support, education, or research software?

The present intended use is clinician-supervised education and research
simulation. It is not clinical decision support for diagnosis or treatment.

## What integrations are required?

The demo accepts structured input and supported uploads. A production pilot
would likely require governed FHIR/SMART integration, identity and access
management, terminology mapping, audit logging, and explicit data-retention
controls.

## How is protected health information secured?

The public demo must use synthetic, de-identified, or appropriately licensed
data. The current local/demo system is not an authenticated multi-user PHI
platform. Production use requires encryption, tenant isolation, least-privilege
access, audit logs, retention/deletion controls, vendor agreements, consent/data
governance, and a security review.

## What is the regulatory path?

Claims and intended use determine the path. The current product is limited to
supervised education/research simulation. Patient-specific recommendations or
outcome prediction would require formal regulatory analysis and substantially
more clinical validation before release.

## Is this clinically validated?

No. BeatIT is educational simulation software. It borrows verification,
validation, uncertainty, and evidence-discipline practices without claiming
FDA, regulatory, or clinical validation.

## Where does physiology come from?

The deterministic Python physiology core and its versioned tests. LLMs do not
perform the cardiac calculations.

## Why not just use an LLM?

The LLM is optional and limited to explanation/extraction/orchestration. The
numerical state, seeded ensemble, Shadow Trial pairing, and sensitivity outputs
come from deterministic code with provenance.

## What is patient-specific?

Only the evidence-backed state and its derived projections for the selected
case. The demo fixture is synthetic and labeled as such.

## How is uncertainty calculated?

M8 uses bounded deterministic perturbation and descriptive accepted-sample
spread over declared inputs. It is not a posterior, probability, confidence
interval, or clinical risk estimate.

## What happens without the model or internet?

The deterministic core, local fixture, procedural heart, and safe fallback
paths remain available. Optional explanations are degraded or unavailable.

## Could this recommend treatment?

No. Safety gates block diagnosis, treatment, and emergency guidance language.

## How do you validate the twin?

Formula invariants, golden fixtures, deterministic replay, bounded contract
tests, provenance audits, and explicit known limitations. This is engineering
credibility evidence, not clinical validation.
