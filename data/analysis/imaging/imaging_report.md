# HeartTwin CareGuard — CT Imaging + VISTA Analysis

_Generated 2026-07-18T23:36:47+00:00_

> Research/software-testing only. VISTA output is model-derived research segmentation requiring clinician review. CT is fused into a clinical case only on independently verified same-subject linkage.

## Linkage
- Clinical cases: **1000** | with actual CT: 0
- Verified same-subject CT: **0** | no-linked-CT: 1000
- Imaging-only benchmark (real CT): **3** | prohibited pairings: 0

## Sources
- `multid4cad`: access_pending (max 118)
- `imagecas`: access_pending (max 1000)
- `totalsegmentator`: access_verified (max 1228)
- `tcia`: access_pending (max 0)
- `rad-chestct`: access_pending (max 0)

## VISTA endpoint
- configured: False | reachable: False (static_fallback)
- supported classes: ['heart', 'aorta', 'pulmonary artery']
- jobs: 3 | states: {'failed': 3}

## Segmentation
- reference masks available: 3
- metrics computed: 0 (gated: no live VISTA endpoint; no masks fabricated)

## Fusion
- verified fusions: 0 | blocked: 3
- adversarial demographic match → **prohibited_cross_dataset_match** (correctly blocked)

## Strongest supported claim
Real CT volumes were ingested, validated (DICOM + NIfTI), and prepared for VISTA with only endpoint-declared classes; every fusion into a clinical case is gated on verified same-subject linkage, and an adversarial demographic match is provably rejected.

## Claims NOT supported
- No CT belongs to any eICU patient. No live VISTA segmentation ran (gated). No segmentation accuracy is claimed. No diagnosis is derived from imaging.