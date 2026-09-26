# The problem BeatIT addresses

## Summary

Cardiovascular care draws on evidence that differs in format, time, and
epistemic strength: history, vital signs, ECG, echocardiography, CT or MRI,
laboratory results, medications, and narrative reports. Health information
exchange can improve access to records, but access alone does not turn those
records into an inspectable physiological model. A clinician who wants to
explain a bounded hypothetical change must still connect the evidence, the
assumptions, the calculation, and its uncertainty.

This matters in a disease area with substantial burden. The World Health
Organization describes cardiovascular diseases as the leading cause of death
globally and estimates 17.9 million deaths in 2019. These population figures
establish importance; they do not establish demand for BeatIT or validate its
clinical utility.

Sources:

- [WHO: Cardiovascular diseases (CVDs)](https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds))
- [CDC: Heart Disease Facts](https://www.cdc.gov/heart-disease/data-research/facts-stats/index.html)
- [ASTP/ONC: Health Information Exchange](https://www.healthit.gov/topic/health-it-and-health-information-exchange-basics/health-information-exchange)

## The workflow gap

Three useful capabilities often remain separate:

1. **Clinical records** preserve observations and support care workflows.
2. **Computational models** can represent explicit physiological relationships
   and run controlled simulations.
3. **Language models** can organize and explain information, but generated text
   is not a safe source of canonical physiological calculations.

Separation creates practical questions that a record viewer or prose summary
alone cannot answer:

- Which displayed values came directly from supplied evidence?
- Which were extracted, derived, inferred, prior-filled, or simulated?
- What assumptions and bounds produced a hypothetical result?
- Would identical inputs reproduce the same baseline?
- Which missing or uncertain inputs materially influence a modeled output?
- Can a clinician inspect the calculation without accepting generated prose as
  numerical authority?

Reviews of digital-twin research describe similar translation challenges,
including heterogeneous data, model personalization, validation, uncertainty,
interoperability, and integration into clinical workflows. BeatIT does not
claim to have solved those field-wide challenges.

- Corral-Acero et al.,
  [The “Digital Twin” to enable the vision of precision cardiology](https://doi.org/10.1093/eurheartj/ehaa159),
  *European Heart Journal* (2020).
- Niederer et al.,
  [Creation and application of virtual patient cohorts of heart models](https://doi.org/10.1098/rsta.2019.0580),
  *Philosophical Transactions of the Royal Society A* (2020).

## BeatIT's implemented response

The repository implements an educational and research simulation workflow:

```text
supplied evidence
      ↓
source-labelled cardiac state
      ↓
deterministic calculations
      ↓
bounded hypothetical scenario
      ↓
baseline/simulation comparison
      ↓
descriptive uncertainty and evidence-priority views
```

The Python engine owns canonical calculations such as stroke volume, ejection
fraction, cardiac output, mean arterial pressure, and QT correction. Scenario
controls are bounded and preserve the originating snapshot. Seeded
plausible-twin ensembles expose accepted and rejected samples. “Shadow Trial”
pairs each accepted simulated baseline with its own hypothetical descendant;
it is not a clinical trial. “Missing Piece” applies deterministic sensitivity
and evidence-priority heuristics to modeled targets.

The product also contains provenance/status surfaces, a procedural cardiac
visualization, report generation, safety checks, and optional language and
VISTA-3D adapters. Optional model services may be unavailable without replacing
their output with invented data.

## What remains unresolved

Repository implementation is not clinical evidence. Current limitations
include:

- no clinical validation, calibration study, or demonstrated improvement in
  patient outcomes or clinical workflow;
- incomplete provenance coverage across all displayed values;
- a synthetic fixture as the release-safe demonstration path;
- local-only real-data adapters that are not a public, allowlisted product
  workflow;
- procedural visualization rather than patient-specific cardiac geometry;
- descriptive sampled spread and local sensitivity, not patient probability,
  a confidence interval, or a validated uncertainty model;
- no completed browser/accessibility certification or production-grade
  multi-user security and persistence evidence;
- optional language and VISTA-3D integrations whose availability depends on
  deployment-specific configuration.

The narrow problem statement is therefore: **make bounded cardiovascular
simulation easier to inspect and explain while keeping evidence status,
deterministic calculations, assumptions, and limitations visible.** Whether
that improves clinical communication is a hypothesis for future study.
