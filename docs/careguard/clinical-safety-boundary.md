# CareGuard Clinical Safety Boundary

CareGuard is **clinical decision support**, not an autonomous prescriber. Every
surface carries: *"Clinical decision support draft. Clinician and pharmacist review
required."*

## Hard invariants (enforced in code + tests)

CareGuard **never**:
- prescribes a medication, generates a dose, or modifies a signed order
- claims a medication/alternative is "safe", "best", "optimal", or "clinically approved"
- diagnoses a new morbidity or invents a lab value
- guarantees an adverse event will/won't occur
- converts a SIDER signal, DDInter record, or adverse-event report into a contraindication
- treats a report mention as a confirmed diagnosis

## Hard block (`blocked_for_draft`) requires one of

1. a current **official label** listing the patient's documented factor as a contraindication,
2. a documented **allergy** matching the active ingredient,
3. an unintentional **duplicate active ingredient**,
4. a configured institutional rule.

Otherwise severity is `high_concern` / `caution` / `informational` /
`insufficient_evidence`. Supplemental sources (DDInter/SIDER/DrugCentral) never hard-block.

## Report mentions

Extracted deterministically with negation / temporality / experiencer detection. A
`possible_report_mention` requires clinician confirmation and can **never**
independently trigger a hard block. Negated / family-history / ruled-out mentions are
not treated as patient morbidities.

## Deidentification boundary

Before any deidentify-only model (Fable), identifiers (names, addresses, phones,
emails, MRNs, DOBs, exact dates) are stripped and a defense-in-depth
`assert_no_identifiers` check runs. Raw FHIR bundles, raw reports, raw prompts, and
model reasoning are never stored or logged (`CAREGUARD_LOG_RAW_MODEL_*` default false).

## The critic gate

The clinical critic blocks display when a candidate lacks evidence, a conflict lacks
label evidence, an allergy is ignored, renal review is skipped, a dose appears,
certainty is implied, a guideline version is absent, or a refusal is misrepresented as
success. `safe_to_display=false` withholds the draft until revised.

## Model refusal

Fable may refuse with HTTP 200 (`stop_reason="refusal"`). CareGuard detects this,
records redacted refusal metadata (never content), retries on the Sonnet fallback,
and on double failure returns a safe abstention — it never stores an empty result as a
valid answer or fabricates a replacement.
