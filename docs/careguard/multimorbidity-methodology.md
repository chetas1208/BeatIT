# CareGuard — Multimorbidity Methodology

See `medication-safety-research.md` for the full pipeline. Summary: recorded FHIR
conditions are `recorded_active` / `recorded_historical`; report mentions are extracted
deterministically with negation/temporality/experiencer cues and classified
(`possible_report_mention` / `negated` / `family_history` / `ruled_out` / `uncertain`).
A possible mention requires clinician confirmation and can never independently trigger a
hard block; negated/family/ruled-out mentions are not treated as patient morbidities.
The cross-organ matrix (`risk/cross_organ_matrix.py`) records facts and gaps per domain
(cardiac/renal/hepatic/pulmonary/metabolic/bleeding/allergy/pregnancy/frailty/
drug_interaction/missing_evidence) and marks `unknown` rather than fabricating an "ok".
No new condition is ever diagnosed.
