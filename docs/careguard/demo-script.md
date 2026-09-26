# CareGuard Demo Script (3 minutes)

Synthetic FHIR only. Backend flag-on; frontend at `/careguard`.

**0:00–0:25 — Problem.** "Cardiac care decisions rarely involve only the heart.
Clinicians must reconcile guidelines with kidney function, pulmonary disease,
allergies, medications, missing labs, and patient-specific evidence."

**0:25–0:50 — Import.** Import the Abridge-style bundle (`cardiorenal-bundle`). Show:
13 FHIR resources parsed; context reconstructed (HFrEF + CKD 3b + COPD, meds, sulfa
allergy); every fact links to its JSON pointer; **missing potassium** flagged.

**0:50–1:25 — Evidence & conflict.** Run the review. Show the AHA/ACC/HFSA 2022 MRA
monitoring passage and KDIGO 2024; RxNorm-normalized meds; the **spironolactone
official-label** hyperkalemia/renal contraindication (`blocked_for_draft`); the
cross-organ matrix (renal caution, pulmonary caution, missing-evidence high); a
DDInter supplemental drug–drug lead (spironolactone + lisinopril).

**1:25–1:55 — Candidates & alternatives.** Show 3 care-plan options (continue-with-
monitoring, obtain-evidence-first, cautionary-escalation). Medication alternatives:
**eplerenone excluded** (same-class MRA, same hyperkalemia risk), **dapagliflozin — a
lower documented conflict burden candidate** (SGLT2i named by the guideline, label
re-checked, no hyperkalemia), **empagliflozin — requires more information** (no label).
Reasons for/against, missing potassium, clinician-review status.

**1:55–2:20 — DualBeat simulation.** Run the bounded comparison (EF 32%). "This is not
outcome prediction — it is a deterministic physiologic scenario comparison with
explicit uncertainty," reusing DualBeat's existing tested functions; baseline unchanged.

**2:20–2:40 — Clinical critic.** Show the critic blocking anything unsourced / dosed /
uncertain, and its scorecard.

**2:40–3:00 — Decision & value.** Clinician accepts / rejects / requests pharmacist
review / overrides (with required reason). Show the audit trail. Close: "CareGuard does
not choose treatment. It finds cross-condition safety conflicts that may be missed when
care is reviewed one organ at a time, then presents evidence-linked candidates and
missing information for clinician and pharmacist review."
