# BeatIT healthcare product plan

## Product thesis

**BeatIT helps cardiologists explain and explore bounded recovery scenarios using
patient data and deterministic cardiovascular modeling—without allowing an LLM
to invent clinical calculations.**

The initial user is a cardiologist preparing for or conducting a supervised
recovery/follow-up conversation. Recovery planning is difficult to personalize
and explain because evidence, physiological models, uncertainty, and care-team
reasoning are usually separated across reports and tools.

## Intended use

Clinician-supervised education and communication using inspectable cardiovascular
simulations. BeatIT organizes supplied evidence, creates a reproducible baseline,
and compares bounded hypothetical scenarios.

## Unsupported use

BeatIT is not clinically validated and is not a medical device. It must not be
used for diagnosis, treatment or medication selection, emergency triage,
autonomous care decisions, or validated patient-outcome prediction.

## Differentiated capability

The language layer does not predict physiology. Deterministic, tested code owns
the calculations. AI may structure evidence, operate the model, and explain the
result, while the product exposes:

- the source and status of each input;
- the formula/model version behind derived values;
- the exact bounded assumptions behind a scenario;
- baseline-versus-simulation differences;
- uncertainty and missing evidence;
- unsupported conclusions and safety limits.

This is the core novelty. Multi-agent orchestration and external providers are
supporting implementation details.

## Primary workflow

1. The cardiologist opens a synthetic, de-identified, or appropriately governed
   case before a recovery conversation.
2. BeatIT ingests structured evidence and records provenance.
3. The deterministic core produces a reproducible baseline state.
4. The clinician asks an educational physiology question.
5. The clinician changes one bounded scenario parameter.
6. BeatIT calculates and compares the simulated trajectory.
7. AI explains the mathematical drivers, assumptions, limitations, and missing
   evidence without giving advice.
8. The clinician exports or summarizes the comparison for supervised education.

## Evidence strategy

Engineering credibility requires golden expected-versus-produced outputs,
repeatability across fresh runs, boundary tests, provenance audits, safety red
teams, and documented limitations. Preliminary clinician feedback may support
workflow relevance but must never be presented as clinical validation.

## Business hypothesis

The likely initial buyer is a cardiac rehabilitation program, cardiology service
line, or clinical education organization. Adoption begins as supervised
education/workflow software, not autonomous decision support. A pilot should
measure preparation time, patient comprehension, clinician explanation burden,
and safe completion—not health outcomes unless a properly designed study exists.

Production adoption would require authenticated access, tenant isolation, audit
logs, encryption, retention/deletion controls, consent and data-use agreements,
validated EHR integration (likely FHIR/SMART), security review, and a formal
regulatory assessment. Claims determine regulatory posture; any move toward
patient-specific recommendations or outcome prediction materially raises the
burden.

## Priorities

1. Reliable baseline-to-scenario workflow.
2. Provenance and value-status completeness.
3. Assumptions, bounds, uncertainty, and limitations.
4. Golden, repeatability, and safety evidence.
5. Deployed demo and backup.
6. Pitch, buyer path, and roadmap.
7. Optional infrastructure and additional visual polish.

## Roadmap

- **Now:** educational simulation demonstrator with deterministic golden cases.
- **Next:** clinician workflow feedback, usability evidence, and secure
  de-identified pilot infrastructure.
- **Later:** governed EHR integration and prospective validation appropriate to
  the intended claims; pursue regulatory analysis before expanding intended use.
