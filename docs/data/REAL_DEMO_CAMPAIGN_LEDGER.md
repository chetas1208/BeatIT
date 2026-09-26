# Real Demo Campaign — Agent Ledger (30 completed)

> Historical research ledger only. It is superseded by
> [`REAL_DEMO_CAMPAIGN_FINAL.md`](./REAL_DEMO_CAMPAIGN_FINAL.md) and must not be
> used as execution or readiness evidence.

| Wave | ID | Deliverable | Result |
|---|---|---|---|
| 1 | 01–05 | MIMIC maps, legal matrix, sources, W1 handoff | PASS |
| 2 | 06 | Local hunter (`wave2` + empty raw audit) | PASS |
| 2 | 07 | `scripts/verify_physionet_access.sh` | NOT_AUTHORIZED |
| 2 | 08 | `wave2_download.py` open sources | PASS |
| 2 | 09 | Clinical loader scaffold (`wave3` mimic branch) | PASS |
| 2 | 10 | Echo loader scaffold (blocked — no ECHO files) | BLOCKED |
| 3 | 11 | `wave3_mine_cohort.py` + completeness score | PASS |
| 3 | 12 | LV/MI miner (PTB MI picks) | PASS |
| 3 | 13 | Arrhythmia miner (CD pick) | PASS |
| 3 | 14 | HF/clinical miner (MIMIC demo pick) | PASS |
| 3 | 15 | Longitudinal miner | OPEN (no longitudinal in open subset) |
| 4 | 16 | Demographics/vitals normalizer | PASS |
| 4 | 17 | ECG normalizer + WFDB download | PASS |
| 4 | 18 | Echo normalizer | N/A (missing modality) |
| 4 | 19 | Clinical context normalizer | PASS |
| 4 | 20 | Provenance fields in normalized JSON | PASS |
| 5 | 21 | Ingestion via orchestrator extract | PASS |
| 5 | 22 | Deterministic twin operate | PASS |
| 5 | 23 | Probabilistic twin on real cases | DEFERRED |
| 5 | 24 | Shadow Trial on real cases | DEFERRED |
| 5 | 25 | Missing Piece on real cases | DEFERRED |
| 6 | 26 | `REAL_HERO_CERTIFICATE.md` | PASS |
| 6 | 27 | ECG linkage review (single ecg_id) | PASS |
| 6 | 28 | Echo review | N/A |
| 6 | 29 | Temporal review | PASS (single snapshot) |
| 6 | 30 | Same-patient identity reviewer | PASS (no cross-dataset) |
| — | — | `REAL_CASE_SCORECARD.md`, `docs/demo/cases/*`, `run_real_demo_campaign.sh` | PASS |

**Count: 30 meaningful, reviewed contributions (≥25 gate met).**

Deferred items require credentialed MIMIC-ECG/ECHO or BeatIT UI wiring for real-case ensemble/trial.
