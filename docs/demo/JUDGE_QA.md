# Judge Q&A

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
