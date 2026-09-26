# CareGuard — Medication Evidence Policy

See `medication-source-matrix.md` for the source tiers. Key rules
(`medications/evidence_policy.py`):

- A hard block (`blocked_for_draft`) requires a hard-block-capable source (official
  DailyMed/openFDA label or approved local label) — enforced when
  `CAREGUARD_REQUIRE_OFFICIAL_LABEL_FOR_HARD_BLOCK=true`.
- DDInter/SIDER/DrugCentral/RxNorm/RxClass are supplemental — never a hard block.
- SIDER can never block and never marks an alternative "safer".
- DDInter alternative leads are never displayed until independently verified.
- Adverse-event reports are never converted into verified contraindications.
- No interaction is invented; when no official label is retrievable, CareGuard reports
  `drug-label evidence unavailable` / `insufficient_evidence`.
- DrugBank refuses to load without `DRUGBANK_LICENSE_CONFIRMED=true`.
