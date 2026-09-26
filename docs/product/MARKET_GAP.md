# Market and workflow gap

## Positioning

BeatIT is an educational cardiovascular simulation demonstrator. It explores a
gap between record-centric clinical systems, language-centric assistants, and
research-oriented mechanistic modeling. This is conceptual positioning, not an
exhaustive vendor comparison, market-size estimate, or claim that no competing
product combines these capabilities.

| Category | Typical strength | Gap relevant to BeatIT |
|---|---|---|
| EHR and health-information systems | Recording, retrieving, exchanging, and documenting clinical information | Access to records does not itself provide a patient-state simulation, bounded counterfactual model, or model-uncertainty explanation |
| General-purpose language models | Summarization, question answering, and natural-language interaction | Generated text is not a reliable canonical authority for physiological arithmetic; grounding, provenance, and safe failure remain necessary |
| Mechanistic and digital-twin research | Explicit models, simulation, and virtual cohorts | Translation can require specialist modeling expertise, validated personalization, uncertainty treatment, and clinical-workflow integration |
| BeatIT | Inspectable evidence-to-simulation workflow with deterministic numerical authority | Not clinically validated, not production-ready for patient data, and not a diagnostic or treatment system |

The descriptions above concern broad categories. Individual products and
research systems vary materially.

## Evidence for the gap

### Records are necessary but not equivalent to a model

The US health-IT program describes health information exchange as electronic
movement of health information among organizations. Interoperability and access
are foundational, but they do not establish a mechanistic model or determine
the meaning of a hypothetical physiological change.

- [ASTP/ONC: Health Information Exchange](https://www.healthit.gov/topic/health-it-and-health-information-exchange-basics/health-information-exchange)
- [HL7 FHIR overview](https://www.hl7.org/fhir/overview.html)

### Language generation needs bounded authority

Medical large-language-model literature reports useful language capabilities
alongside limitations involving factuality, evaluation, bias, privacy, and
clinical deployment. The FDA's clinical decision support guidance also
emphasizes the importance of whether a health-care professional can
independently review the basis for a recommendation. BeatIT adopts the narrower
engineering rule that external language models may extract, route, or explain,
but may not silently replace canonical physiology.

- Singhal et al.,
  [Large language models encode clinical knowledge](https://doi.org/10.1038/s41586-023-06291-2),
  *Nature* (2023).
- World Health Organization,
  [Ethics and governance of artificial intelligence for health](https://www.who.int/publications/i/item/9789240029200)
  (2021).
- US Food and Drug Administration,
  [Clinical Decision Support Software: Guidance for Industry and FDA Staff](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software)
  (2022).

These sources do not evaluate BeatIT.

### Mechanistic models face translation and validation barriers

Cardiovascular digital-twin literature presents a path toward personalized
modeling while identifying hard problems in data assimilation, parameter
identification, uncertainty, validation, and clinical adoption. Virtual cohorts
can support controlled computational experiments, but they are not substitutes
for clinical trials or clinical outcome evidence.

- Corral-Acero et al.,
  [The “Digital Twin” to enable the vision of precision cardiology](https://doi.org/10.1093/eurheartj/ehaa159)
  (2020).
- Niederer et al.,
  [Creation and application of virtual patient cohorts of heart models](https://doi.org/10.1098/rsta.2019.0580)
  (2020).
- Viceconti et al.,
  [In silico trials: Verification, validation and uncertainty quantification of predictive models used in the regulatory evaluation of biomedical products](https://doi.org/10.1016/j.ymeth.2020.01.011),
  *Methods* (2021).

## BeatIT's differentiated hypothesis

BeatIT attempts to join five operations in one inspectable workflow:

1. preserve supplied evidence and its status;
2. build a reproducible baseline with deterministic code;
3. run a bounded hypothetical branch without mutating the observed snapshot;
4. compare paired simulated states across plausible input samples;
5. expose model assumptions, limitations, sensitivity, and evidence priority.

Its architectural distinction is not “AI cardiology.” It is the separation of
authority:

| Function | Current authority |
|---|---|
| Canonical cardiovascular arithmetic and scenario propagation | Versioned Python code |
| Plausible-twin sampling and paired simulation | Seeded, bounded code |
| Sensitivity and evidence-priority heuristics | Deterministic Missing Piece engine |
| Language explanation and orchestration | Optional provider with deterministic fallback and output checks |
| Image segmentation | Optional VISTA-3D adapter; not required for the deterministic workflow |

## Commercial and adoption hypotheses

No customers, procurement decisions, or measured willingness to pay are
established by this repository. Plausible early evaluation settings are
cardiology education, cardiovascular research, and supervised communication
workflows in academic or research institutions. Potential institutional
stakeholders could include cardiology service lines, cardiac rehabilitation
programs, academic medical centers, and cardiovascular research groups.

Before commercial or clinical deployment, BeatIT would need evidence and
controls beyond the current repository, including:

- formative user research with clinicians and intended audiences;
- validated task definitions and usability studies;
- clinical and analytical validation proportionate to intended claims;
- authentication, authorization, tenant isolation, encryption, auditing,
  retention, deletion, and incident-response controls;
- governed interoperability and data-use agreements;
- deployment-specific privacy, security, and regulatory assessment;
- prospective evidence before any claim about outcomes, efficiency, or patient
  understanding.

## Claims this document does not make

- BeatIT has no competitors.
- Every EHR, language model, or simulation platform has the same limitations.
- BeatIT is clinically superior to an existing workflow.
- BeatIT predicts patient outcomes or treatment effects.
- “Shadow Trial” is a clinical trial.
- The repository establishes a market size, active buyer demand, regulatory
  status, or production readiness.
