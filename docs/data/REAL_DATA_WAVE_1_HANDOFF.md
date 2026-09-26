# Wave 1 Handoff — Real Demo Case Campaign

Date: 2026-09-26

## Locked decisions

| Item | Decision |
|---|---|
| **Primary hero architecture** | Single `subject_id` across MIMIC-IV clinical + MIMIC-IV-ECG + MIMIC-IV-ECHO |
| **Secondary cases** | PTB-XL (ECG-only), EchoNet (echo-only), MIMIC-IV Demo (clinical-only dev) — **separate cases** |
| **Synthetic cohort** | Remains for hackathon **SHIP** path; **real campaign replaces strategy for “real demo”**, not retroactive relabeling of SYNTHETIC demo |
| **Storage** | `data/real/` gitignored; manifests in `docs/data/` and `data/real/*.json` metadata-only where permitted |

## Access status (this host — no secrets inspected)

| Source | Status |
|---|---|
| PhysioNet home (`~/.physionet`) | **Not present** |
| MIMIC-IV full | **NOT AUTHORIZED / NOT DOWNLOADED** (`data/raw/mimic-demo/` empty) |
| MIMIC-IV-ECG | **NOT PRESENT** |
| MIMIC-IV-ECHO | **NOT PRESENT** |
| PTB-XL | **NOT PRESENT** (placeholder `data/raw/ptb-xl/`) |
| EchoNet | **NOT PRESENT** |

**Interpretation:** Wave 2 must run `scripts/verify_physionet_access.sh` and local hunter before any download. Do **not** bulk-fetch credentialed data until status is **AUTHORIZED**.

## Download strategy (Wave 2+)

1. Complete PhysioNet credentialing on this account (human subjects + DUA) if not already done elsewhere.
2. Install PhysioNet client; download **MIMIC-IV Demo** first (open) to validate loaders — still **not** multimodal hero.
3. After cohort query (Wave 3): targeted ECG waveform fetch for shortlisted `subject_id` only.
4. PTB-XL: single open download for one **ECG-focused** real demo case if MIMIC blocked.

## Data boundaries

- Legacy `data/scripts/05_select_ptbxl.py` **must not** be reused to attach PTB-XL ECG to unrelated cohort patients for “real demo.”
- `data/analysis/mimic_validation_cohort.json` is **aggregate validation** from an earlier demo run; not a BeatIT case pack.

## Wave 2 agent queue

| ID | Task |
|---|---|
| 06 | Local dataset hunter (expand search under `/usr/data/923873155`) |
| 07 | PhysioNet access verifier script |
| 08 | ECG indexer (PTB-XL open OR MIMIC-ECG if authorized) |
| 09 | MIMIC clinical loader scaffold |
| 10 | MIMIC-ECHO loader scaffold |

## Blockers before hero case

1. **Credentialed MIMIC-IV + ECG + ECHO local presence**
2. Cohort query tooling (Wave 3)
3. BeatIT ingestion contract for real WFDB + echo CSV (Wave 5)

**HERO CASE READY: NO** (expected after Wave 1)

---

## Post-campaign update (all waves executed)

See `REAL_DEMO_CAMPAIGN_FINAL.md`. **ECG-focused hero READY** (`REAL-DEMO-PTB-000008`).
**Multimodal MIMIC hero still NO** until credentialed ECG+ECHO+clinical on one `subject_id`.
Run: `./scripts/run_real_demo_campaign.sh`
