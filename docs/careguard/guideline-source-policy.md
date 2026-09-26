# CareGuard — Guideline Source Policy

Local-first retrieval: search approved local corpus → check version/effective date →
retrieve the exact passage → compute citation metadata (hash) → use official web sources
only when the document is missing AND `CAREGUARD_ALLOW_EXTERNAL_RESEARCH=true`.

Authority hierarchy: (1) clinical/regulatory (FDA labeling, DailyMed, ACC/AHA/HFSA,
KDIGO, ADA, FDA CDS guidance); (2) interoperability (FHIR R4, US Core, SMART, CDS Hooks);
(3) peer-reviewed research (architecture/signal/segmentation only); (4) internal docs.

A research paper is **never** used in place of a clinical guideline when generating a
candidate care-plan review (`evidence/source_policy.py::can_ground_recommendation` →
authority level 1 only). A guideline recommendation is never claimed without a verifiable
passage; the agent abstains otherwise. Guidelines are age-exempt from staleness (valid
until superseded); undated/missing-version/explicitly-superseded sources are excluded.
