# CareGuard — Abridge / FHIR R4 Mapping

CareGuard ingests FHIR R4 Bundles via its own route (`POST /fhir/import`) and parser —
DualBeat's upload path is untouched.

Parsed resources: Patient, Encounter, Condition, Observation, DiagnosticReport,
MedicationRequest, MedicationStatement, AllergyIntolerance, Procedure, ImagingStudy,
ServiceRequest, CarePlan, Goal, DocumentReference, Practitioner, Organization.
Unsupported resources are **recorded** in the validation summary, not dropped.

Validation checks resourceType/Bundle type, unique ids, resolvable references, required
status fields, coding systems, units, and duplicates. Every extracted value becomes a
`ClinicalFact` with a `json_pointer` (RFC 6901) back to its source field, an
`assertion_type` (`recorded` / `derived_deterministically` / `model_inference` /
`missing`), a code system (SNOMED/LOINC/RxNorm/ICD/UCUM preserved verbatim, never
invented), and a confidence. A model inference never becomes a recorded fact.
