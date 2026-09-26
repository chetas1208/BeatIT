# Multimorbidity Medication Safety — Methodology & Research

## Problem

Cardiac care decisions rarely involve only the heart. A clinician focused on one
organ can miss conflicts arising from kidney/liver/lung disease, allergies, other
medications, missing labs, or morbidities documented only in a report. CareGuard
reviews every proposed/active medication against the patient's **complete** documented
context and surfaces evidence-linked, lower-conflict candidates for review.

## Pipeline (deterministic; Claude optional)

1. **Reconcile medications** — RxNorm identity, ingredient decomposition, brand/generic
   + duplicate detection, ambiguity → clinician confirmation (`medication_reconciler`).
2. **Reconcile morbidities** — FHIR Conditions (recorded_active/historical) + report
   mentions with negation/temporality/experiencer (`morbidity_reconciler`, `reports/`).
3. **Cross-organ signals** — renal/hepatic/pulmonary/metabolic/bleeding/allergy/
   pregnancy/frailty from recorded facts only (`risk/signals.py`).
4. **Conflict engine** — drug–drug, drug–disease, drug–organ, allergy, therapeutic
   duplication, monitoring gap; each backed by an official-label passage or reported as
   `insufficient_evidence` (`conflict_engine.py`).
5. **Alternative engine** — generic-equivalent (Orange Book), same-class (RxClass +
   guideline), cross-class (guideline-named); every candidate re-run through the full
   conflict engine; equal/stronger conflict → excluded; never ranked "best"
   (`alternative_engine.py`).
6. **Safety critic** — blocks unsourced hard conclusions, unverified alternatives,
   doses, banned language, report-mention-as-fact (`safety_critic.py`).

## Alternative-generation policy

- Candidates never come from model memory.
- Generic equivalents are excluded when the ingredient itself is the conflict source.
- Same-class members require guideline grounding and are re-checked; hyperkalemia-risk
  MRAs (e.g. eplerenone) are **excluded** for a reduced-eGFR / unknown-potassium patient.
- Cross-class options must be **explicitly named** by an applicable guideline passage
  (e.g. an SGLT2 inhibitor for HFrEF), then re-checked and given complete evidence.
- Ranking is by evidence completeness, conflict burden, freshness, and missing-fact
  count — surfaced as *lower documented conflict burden* / *requires more information* /
  *excluded due to documented conflict* / *insufficient evidence*, never *safest/best*.
- When nothing qualifies: *"No adequately supported lower-conflict medication candidate
  was identified from the configured evidence sources."*

## Indexed research (see `research-manifest.yaml`)

Interaction/label databases (RxNorm, RxClass, DailyMed, openFDA, Orange Book, DDInter
2.0, DrugCentral, SIDER); multimorbidity/polypharmacy literature (drug–disease
interaction alerts, deprescribing, structured medication review); FHIR R4 +
CDS Hooks; and the cardiac technical basis (EchoNet-Dynamic, PTB-XL, Pan–Tompkins,
CAMUS, VISTA-3D). A research paper is never used in place of a guideline when proposing
a clinical candidate.
