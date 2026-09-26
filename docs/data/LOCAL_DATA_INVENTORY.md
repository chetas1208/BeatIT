# BeatIT Local Data Inventory

## Current campaign boundary

- `data/synthetic_cohort_500/`: canonical 500-profile synthetic cohort created
  by this campaign; all identities are `BEATIT-SYN-0001` through
  `BEATIT-SYN-0500`.
- `fixtures/hearttwin/` and `fixtures/golden/`: checked-in synthetic fixtures
  for deterministic cardiac, ECG, ensemble, and Shadow Trial tests.
- `data/imaging-cases/`: isolated imaging artifacts and manifests; not joined to
  synthetic cohort identities.
- `data/cohort/` and `data/analysis/`: historical/public-derived aggregate
  tables and manifests; they are not used to create the 500 synthetic profiles.

The local raw eICU/PTB-XL/EchoNet per-case payload trees are not treated as
available source inputs for this campaign. Their references remain separate and
are marked partial where applicable.

## Identity rule

No PTB-XL, NHANES, eICU, or imaging record is attached to a synthetic profile.
Public/reference materials may inform format or broad sanity checks only.
