# Agent 29 — Data Manifest Verification

Date: 2026-09-26 UTC
Scope: `data/manifest.json`, the checked-in release-golden manifest, referenced
fixture checksums, synthetic/provenance labels, and fixture completeness.

## Disposition

**PARTIAL — checksum and path integrity pass; semantic classification and
provenance completeness remain open.** No fixture or manifest files were
modified by this audit.

The checked-in release data is suitable for a synthetic, educational demo
only. It is not evidence of patient data, clinical validity, or a complete
provenance chain for every source artifact.

## Verification performed

The following read-only checks were run:

- `./scripts/verify-demo.sh` — **PASS** (`DEMO FIXTURES PASS`, `DEMO VERIFY PASS`).
- Recomputed SHA-256 digests for every entry in `data/manifest.json` — **3/3
  paths present and matching**.
- Recomputed SHA-256 digests for every role in
  `fixtures/golden/release_demo/manifest.json` — **8/8 roles present and
  matching**.
- Compared `fixtures/hearttwin/README.md` with the twelve generator targets in
  `scripts/create_synthetic_fixtures.py` — **12/12 documented, generated, and
  present**.
- Parsed both manifests and inspected the referenced JSON metadata — **PASS**.

The release-golden builder contract was inspected but not run, because this
task is documentation-only and must not rewrite an existing manifest.

## `data/manifest.json`

| Check | Result | Evidence |
|---|---|---|
| JSON parses | PASS | `data/manifest.json` |
| Dataset version | PASS | `m10.5-demo-v1` |
| Dataset-level synthetic flag | PASS | `synthetic: true` |
| Dataset-level provenance label | PASS | `provenance_classification: synthetic_demo` |
| Referenced files | PASS | 3/3 checksum paths exist |
| Checksums | PASS | 3/3 recomputed SHA-256 values match |
| Fixture IDs | PARTIAL | `manual_baseline`, `fixed-only`, `synthetic-demo-case` are listed; only the first and third have an explicit top-level fixture/name field |

The three verified hashes are:

| Path | SHA-256 |
|---|---|
| `fixtures/hearttwin/manual_baseline.json` | `1e448677700a64058df5038dd60f8f5a6516dc2df9bff5eb5e71f6fbd335b5ca` |
| `fixtures/golden/probabilistic/fixed-only.json` | `ac3d4334162541b0c4aec6d1cca61210826737f1d82f9295f7ff02c20178fb84` |
| `fixtures/golden/shadow_trials/synthetic-demo-case.json` | `6ab9a8c62f80e1a373ee01ce8d6b8eca8b87041abe694331f5a913b081406530` |

## Release golden manifest

`fixtures/golden/release_demo/manifest.json` declares version
`m10.5-release-demo-v1`, `synthetic: true`, and
`provenance_classification: synthetic_demo`. It has eight source roles but six
unique files because `snapshot`/`ensemble` and `scenario`/`shadow_trial` are
intentional aliases.

| Role | Referenced file | Checksum |
|---|---|---|
| `patient` | `fixtures/hearttwin/manual_baseline.json` | `1e448677700a64058df5038dd60f8f5a6516dc2df9bff5eb5e71f6fbd335b5ca` |
| `events` | `fixtures/hearttwin/ecg_synthetic_normal.csv` | `2430db5eba469b43d2a556f80606e417546c457c28839130885751ca5c30711e` |
| `snapshot` | `fixtures/golden/probabilistic/synthetic-replay.json` | `e101c80bc9ee5522c79d45ecc913a1604495fc274168928198b6a3bb9eb6c1f0` |
| `ensemble` | `fixtures/golden/probabilistic/synthetic-replay.json` | `e101c80bc9ee5522c79d45ecc913a1604495fc274168928198b6a3bb9eb6c1f0` |
| `scenario` | `fixtures/golden/shadow_trials/synthetic-demo-case.json` | `6ab9a8c62f80e1a373ee01ce8d6b8eca8b87041abe694331f5a913b081406530` |
| `shadow_trial` | `fixtures/golden/shadow_trials/synthetic-demo-case.json` | `6ab9a8c62f80e1a373ee01ce8d6b8eca8b87041abe694331f5a913b081406530` |
| `report` | `fixtures/hearttwin/report_baseline.txt` | `f5ad390645ce5a8aadefec17a627cf8e0786559e0f82f6eacd202c222882f8c5` |
| `echo` | `fixtures/hearttwin/echo_metadata_baseline.json` | `7d25820f6b298432a3e2c148be5b21550a7a456c520ec74506ce4f03903feb8c` |

All eight role-to-file mappings exist and match their declared digest.

## Synthetic and provenance classification

### Verified

- `fixtures/hearttwin/README.md` states that all twelve generated fixtures are
  synthetic, non-PHI, inspired by public dataset structure only, and not for
  diagnosis. The generator has twelve matching output targets, and all twelve
  files are present.
- `manual_baseline.json` carries a synthetic/non-PHI description and safety
  note.
- `synthetic-replay.json` carries `origin_quality: synthetic` and an explicit
  `origin_provenance` record with source `synthetic_replay`, fixture
  `synthetic-replay`, and replay ID `golden-synthetic-replay`.
- `synthetic-demo-case.json` expects `origin_quality: synthetic`,
  `patient_evidence: false`, and a required safety disclaimer.
- The release manifest applies the explicit safety boundary: educational
  simulation only; not diagnosis or treatment.

### Open classification issue

`fixtures/golden/probabilistic/fixed-only.json` is included by
`data/manifest.json` under the dataset-wide `synthetic_demo` label, but its
embedded input and output provenance both say `origin_quality: observed` and
its `origin_provenance` array is empty. The fixture rationale calls it a
deterministic non-PHI golden fixture, and there is no evidence that it contains
real patient data; however, `observed` is ambiguous and does not provide an
auditable synthetic source record.

This is a metadata classification mismatch, not a checksum failure. It should
be resolved before claiming that every manifest member has an unambiguous
synthetic provenance classification.

The ECG CSV, report text, and echo metadata are covered by the global release
manifest and the synthetic fixture README/generator, but do not each carry a
separate provenance sidecar. The current evidence therefore supports a
dataset-level synthetic label, not complete per-artifact provenance coverage.

## Fixture completeness

| Inventory | Result | Detail |
|---|---|---|
| `fixtures/hearttwin` README versus generator | PASS | 12/12 documented targets exist |
| `data/manifest.json` checksum inventory | PASS | 3/3 referenced files exist and match |
| Release-golden source roles | PASS | 8/8 roles resolve; 6 unique files |
| Probabilistic golden corpus | INFORMATIONAL | 7 files exist; only `fixed-only.json` and `synthetic-replay.json` are referenced by the two release manifests |
| Shadow-trial golden corpus | INFORMATIONAL | 7 files exist; only `synthetic-demo-case.json` is referenced by the compact release manifest |
| Declared `split_heart` capability | OPEN | Listed in release capabilities, but no dedicated split-heart fixture is in the release manifest |
| Declared `missing_piece` capability | OPEN | Listed in release capabilities, but no dedicated Missing Piece fixture is in the release manifest |
| Declared `provenance` capability | PARTIAL | Provenance fields exist in selected JSON fixtures, but no complete per-source provenance inventory is declared |

The broader golden corpus is not missing files; it is simply not enumerated by
the compact release manifest. The capability rows above are release-manifest
coverage findings, not claims that the corresponding product code is absent.

## Final assessment

| Gate | Disposition |
|---|---|
| Manifest syntax and required release fields | PASS |
| `data/manifest.json` path integrity | PASS |
| Release-golden path integrity | PASS |
| `data/manifest.json` checksums | PASS |
| Release-golden checksums | PASS |
| Synthetic dataset boundary | PASS at dataset level |
| Per-fixture provenance classification | PARTIAL |
| Referenced fixture completeness | PASS |
| Complete capability-fixture coverage | OPEN |

**Agent 29 final disposition: OPEN / DO NOT CERTIFY AS FULLY COMPLETE.** The
canonical synthetic demo artifacts are present and checksum-stable, but the
`fixed-only` provenance label and the compact manifest's unrepresented
`split_heart`/`missing_piece`/full-provenance capabilities must be clarified
before this data manifest can be treated as a complete release inventory.
