# M10 Demo, Pitch, and Judge Q&A Review

Date: 2026-09-26 UTC  
Contribution: A18  
Scope: `docs/demo/DEMO_SCRIPT.md`, `docs/demo/PITCH.md`, and
`docs/demo/JUDGE_QA.md` compared with the implemented BeatIT product surface,
the deterministic backend contracts, and the M10 safety boundary.

## Verdict

**PASS WITH REQUIRED NARRATION GUARDRAILS — synthetic educational demo only.**

The five-space flow and the principal claims are grounded in implemented UI
and API behavior: TWIN, EXPERIMENT, COMPARE, EVIDENCE, and REPORT; a procedural
beating heart; bounded scenario controls; plausible-twin and same-sample
Shadow Trial panels; sensitivity/evidence prioritization; provenance IDs; and
report limitations. The demo must remain on the seeded synthetic fixture. It
must not be presented as clinical software, a patient-specific prediction, a
treatment comparison, or evidence of efficacy.

## Claim audit

| Source wording | Finding | Release-safe treatment |
|---|---|---|
| “Show the beating heart” | **Supported.** `HeartScene` implements an anatomically suggestive procedural scene whose motion is driven by the selected case's heart rate and EF. | Say “procedural cardiac visualization” or “beating heart visualization”; do not call it an anatomical scan or measurement. |
| “Open its source/provenance context” | **Supported with qualification.** Component and scenario inspectors expose provenance/source IDs, while the report preserves unavailable sections and a source-status legend. | Show the visible `OBSERVED`, `DERIVED`, `SIMULATED`, `PRIOR`, and `SYNTHETIC` labels. A source ID is an audit pointer, not proof of clinical validity. |
| “Run the causal branch” | **Supported.** `ScenarioPanel` exposes bounded parameter controls, Experiment/Reset/Undo/Redo, causal propagation, and a hypothetical-simulation warning. | Call it a deterministic causal propagation branch, not a causal discovery result or clinical intervention model. |
| “Run or select the same-sample paired experiment” | **Supported.** `ShadowTrialPanel` reports requested, valid, and invalid pairs and inspects a selected pair. | State that pairing prevents scenario resampling; it does not establish a treatment effect, benefit, harm, or clinical evidence. |
| “Show baseline versus counterfactual” | **Supported after a valid pair.** Split Heart requires a valid paired result and displays the two simulated sides. | Use “baseline versus hypothetical counterfactual.” Never narrate the delta as a clinical outcome. |
| “Ask ‘Why is this uncertain?’ and ‘What would help?’” | **Needs correction.** The implemented Missing Piece panel uses a target selector and the `Explain uncertainty` action; it is not a free-form question interface. | Say: “Select a modeled target, choose Explain uncertainty, and show the deterministic sensitivity and evidence-priority views.” |
| “Show provenance, unavailable sections, limitations, and the educational disclaimer” | **Supported.** `ReportSurface` renders the disclaimer, status legend, source IDs, unavailable-section language, and interpretation boundaries. | Keep this as a mandatory close, even if the modal disclaimer was previously acknowledged. |
| “The optional intelligence layer is offline…” | **Supported for the verified local fallback path.** The deterministic demo seed and preflight do not require a live language provider, Weave, Redis, VISTA, or internet. | Do not imply that live-provider outage, deployed restart, Redis durability, or public Weave delivery has been release-verified. |
| “What is patient-specific?” | **Unsafe as currently phrased.** The selected case can contain source-backed inputs, but the release fixture is synthetic and the repository does not establish clinical patient-specific validity. | Answer: “The demo is synthetic. A selected case can carry source-labelled inputs and derived simulation outputs, but BeatIT makes no patient-specific clinical prediction or recommendation.” |
| “Safety gates block diagnosis, treatment, and emergency guidance language” | **Too broad for a demo claim.** Safety policies and focused tests exist, but M10 reviews leave generic error envelopes, provenance crosswalks, and some public-surface wording open. | Answer with the narrower verified boundary: “BeatIT is explicitly not for diagnosis or treatment decisions; guarded assistant paths reject prohibited requests, and the demo makes no clinical recommendation.” |
| “How do you validate the twin?” | **Supported only as engineering validation.** Formula invariants, golden fixtures, deterministic replay, contract tests, provenance audits, and known-limitations reviews exist. | Say “engineering verification and reproducibility,” not clinical validation, calibration, regulatory validation, or predictive accuracy. |

## Required three-minute run

Use this exact framing while the release status remains **DO NOT SHIP**:

1. **TWIN:** “This is a procedural visualization of a synthetic case. The
   labels distinguish source-backed values from derived and simulated values.”
2. **EXPERIMENT:** “I am changing one bounded input and recomputing a
   deterministic hypothetical branch; the observed snapshot is unchanged.”
3. **Shadow Trial:** “These are same-sample paired simulations over plausible
   twins. Invalid pairs remain visible, and no effect summary is shown when no
   pair passes validation.”
4. **COMPARE:** “Split Heart compares the selected baseline and hypothetical
   simulation. A delta is not a benefit, harm, treatment effect, or forecast.”
5. **EVIDENCE:** “I select a target and choose Explain uncertainty. The output
   is a local-sensitivity and evidence-priority heuristic, not a probability,
   confidence interval, or information-gain estimate.”
6. **REPORT:** “The report keeps unavailable sections visible, shows source
   status and provenance IDs, and repeats the educational nonclinical
   boundary.”

If any optional provider is unavailable, use the documented recovery line and
show the deterministic result. Do not substitute a fabricated model response,
claim that a cached checkpoint is loaded, or imply that a fallback result has
the authority of a clinical service.

## Approved judge answers

### Is this clinically validated?

No. BeatIT is educational cardiac simulation software. Its tests and reviews
provide software-engineering evidence about deterministic behavior,
reproducibility, safety wording, and bounded contracts; they do not establish
clinical validity, calibration, regulatory compliance, or medical-device
status.

### Where does the physiology come from?

The versioned deterministic Python physiology core and its tests. The optional
language layer may explain, extract, or orchestrate, but it is not the
numerical authority and does not calculate the cardiac state.

### Why not just use an LLM?

Because the demo needs inspectable numerical authority. The scenario branch,
plausible-twin ensemble, same-sample pairing, sensitivity outputs, and report
identifiers are produced by deterministic code with explicit limitations.

### What data is in the demo?

Synthetic fixture data generated and hashed by `scripts/seed-demo.sh`. It is
not a real patient case and must remain visibly labelled as synthetic. Do not
upload identifiable patient data to the current local/file-backed demo path;
authentication, restricted CORS, retention, and hosted multi-user persistence
are not release-proven.

### How is uncertainty calculated?

The M8 view applies bounded deterministic perturbations to declared modeled
inputs and reports descriptive accepted-sample spread/local sensitivity. It is
not a posterior, probability, confidence interval, information-gain estimate,
clinical risk estimate, or forecast guarantee.

### What happens without a model or the internet?

The verified local synthetic path continues with deterministic tools,
procedural visualization, and safe fallback behavior. Optional explanations
may be degraded or unavailable. This does not prove public deployment,
provider-outage, Redis-restart, or browser-visible fault recovery.

### Could this recommend treatment or diagnose someone?

No. The release boundary is educational simulation only and not for diagnosis
or treatment decisions. The presenter must not turn a simulated direction,
metric delta, uncertainty rank, or report phrase into medical advice.

## Presenter stop rules

Stop or fall back to the precomputed synthetic result if:

- the active case is not visibly synthetic;
- a required pair is invalid or no valid effect summary exists;
- provenance, limitations, or the educational disclaimer is hidden;
- the UI shows an unavailable section as if it were a result;
- a judge asks for diagnosis, treatment, emergency guidance, clinical benefit,
  harm, risk, probability, or patient-specific prognosis;
- an optional provider fails and the presenter cannot show the deterministic
  fallback honestly.

## Evidence checked

- `web/components/layout/AppShell.tsx` — frozen five-space routing and mode
  labels.
- `web/components/heart/HeartScene.tsx` — procedural beating visualization.
- `web/components/twin/scenario/ScenarioPanel.tsx` — bounded experiment,
  causal trace, plausible twins, and Shadow Trial entry points.
- `web/components/twin/shadow-trial/ShadowTrialPanel.tsx` — pair validity,
  effect-summary gating, provenance, and hypothetical/synthetic labels.
- `web/components/twin/missing-piece/MissingPiecePanel.tsx` — target selector,
  Explain uncertainty action, sensitivity, evidence ranking, and disclaimers.
- `web/components/product/ReportSurface.tsx` — report status legend,
  unavailable-section language, source IDs, and safety boundary.
- `scripts/seed-demo.sh` and `scripts/demo-preflight.sh` — deterministic local
  fixture and preflight path.
- `docs/hackathon/M10_SCOPE_FREEZE.md`, `docs/hackathon/M10_COMPLETION.md`,
  `docs/hackathon/reviews/M10_SCIENTIFIC_INTEGRITY.md`, and
  `docs/hackathon/reviews/M10_FAILURE_FALLBACK.md` — frozen scope, release
  status, safety findings, and fallback limits.

## Final disposition

The current script, pitch, and Q&A can support a compelling three-minute
synthetic demo after the wording corrections above. They must not be used to
claim public production readiness, clinical utility, patient-specific
prediction, live-provider reliability, or treatment efficacy. This review
changes documentation only; it does not close the M10 deployment, browser,
security, persistence, or scientific-integrity blockers.
