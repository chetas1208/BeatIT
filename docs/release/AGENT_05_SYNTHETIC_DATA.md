# M10.5 Agent 05 — Synthetic Dataset Audit

**Scope:** read-only inspection of the committed synthetic fixtures and the
canonical M10 demo seed. No fixture, source, test, or runtime file was changed
by this audit.

**Audit date:** 2026-09-26 UTC

## Executive result

The repository contains synthetic fixtures for the requested domains, but the
canonical M10 demo seed is narrower than the full fixture inventory.

| Path | Exists in repository | Exercised by canonical M10 seed | Result |
|---|---:|---:|---|
| Longitudinal replay | Yes, executable TypeScript generator | No | Partial |
| ECG waveform | Yes, two CSV fixtures | No | Partial |
| Echo | Yes, two metadata fixtures; no video | No | Partial |
| AHA-17 findings | Generated downstream and covered by test fixtures | No direct fixture payload | Partial |
| Provenance/evidence | Yes in replay, ensemble, Shadow Trial, and test fixtures | Partly | Partial |

The local synthetic core is suitable for an educational demo, but this is not
a single end-to-end dataset proving all five paths. Release claims must keep
that boundary explicit.

## Canonical demo seed

`data/demo/state.json` records hashes for exactly these three files:

1. `fixtures/hearttwin/manual_baseline.json`
2. `fixtures/golden/probabilistic/fixed-only.json`
3. `fixtures/golden/shadow_trials/synthetic-demo-case.json`

`scripts/seed-demo.sh` also runs `scripts/run_local_smoke.py`, which loads only
`manual_baseline.json` and exercises extraction, deterministic operation, and
recovery. It does not load the ECG CSVs, echo metadata, the longitudinal replay
generator, or an AHA finding payload. The Shadow Trial fixture references
`fixtures/golden/probabilistic/synthetic-replay.json`, but that transitive
baseline file is not included in `data/demo/state.json`'s hash list.

The manual baseline is intentionally small and contains only `fixture_id`,
description/label, user vitals, expected deterministic values, and a safety
note. A read-only probe found no `timeline`, ECG, echo, AHA, evidence, or
provenance fields in that object.

## Longitudinal evidence

The longitudinal artifact is implemented as an executable fixture rather than
a JSON data file:

- `fixtures/longitudinal/README.md` documents a stable five-event, two-day
  synthetic replay.
- `web/lib/twin/replay/index.ts` creates five events for EF, heart rate, scar
  fraction, and follow-up EF.
- Every event uses `source: "synthetic_replay"`, a deterministic fixture
  method, evidence IDs, and `REPLAY / DEMO STREAM` labeling.
- `web/lib/twin/integration/context.tsx` constructs this replay timeline for
  the frontend temporal provider.

Therefore the longitudinal/provenance path exists in the frontend product
code, but it is not part of the backend seed smoke or the persisted demo hash
manifest. It was not possible to close this as a canonical end-to-end demo
fixture using the current seed contract.

## ECG coverage

The generator and README define two synthetic CSVs:

- `fixtures/hearttwin/ecg_synthetic_normal.csv`: 2,500 rows,
  `time_ms,lead_ii_mv`, analyzed read-only as 12 peaks, 72.0 bpm, and
  833.5 ms mean RR.
- `fixtures/hearttwin/ecg_synthetic_fast.csv`: 2,500 rows with the same
  columns, analyzed read-only as 20 peaks, 120.0 bpm, and 500.0 ms mean RR.

Both probes returned `method=waveform_analysis` through
`python/hearttwin/tools/ecg_features.py`. The API and extraction layers have
ECG handling, but neither CSV is loaded by `scripts/run_local_smoke.py`,
`scripts/seed-demo.sh`, or `scripts/demo-preflight.sh`. These are therefore
available parser/analyzer fixtures, not canonical demo inputs.

The waveforms are explicitly synthetic ECG-like signals. Their successful
feature extraction must not be presented as clinical ECG interpretation.

## Echo coverage

The repository has:

- `fixtures/hearttwin/echo_metadata_baseline.json`
- `fixtures/hearttwin/echo_metadata_reduced_function.json`

Both contain synthetic echocardiogram metadata with an apical four-chamber
view, EDV/ESV/EF values, LV tracing availability, and end-diastolic/end-systolic
frame numbers. They contain no video frames or image bytes. The inventory and
README describe them as metadata-only fixtures.

The extraction layer contains an echo-video/image path, but no reference from
the canonical seed or local smoke script loads either metadata file. Echo
coverage is consequently present for metadata/schema work but is not proven by
the M10 demo execution path.

## AHA-17 coverage

AHA coverage is generated from a richer cardiac state rather than stored in
the manual demo fixture:

- `python/hearttwin/tools/cardiac_findings.py` emits educational AHA-17
  segment mappings when regional tissue information or qualifying
  electrophysiology/visualization inputs are present.
- `web/lib/heart/__tests__/fixtures.ts` supplies a synthetic regional finding
  with `aha_segments: [1, 17]` and `segment_model: "AHA-17"`.
- `web/lib/twin/comparison/__tests__/regional.test.ts` exercises valid,
  unavailable, malformed, and mismatched regional mappings.
- `python/hearttwin/tests/test_cardiac_findings.py` exercises the backend
  findings layer and safety wording.

A read-only probe applying `derive_findings` to the canonical manual baseline
shape produced zero findings, `segment_model: AHA 17-segment`, and
`imaging_source: none`. This is expected: the baseline has no tissue damage
zone, cardiac findings payload, or image provenance. It demonstrates that the
AHA model is available, not that the canonical seeded case exercises an AHA
regional finding.

## Provenance and evidence coverage

Coverage is strongest in the golden and executable replay artifacts:

- `fixtures/golden/probabilistic/synthetic-replay.json` is explicitly marked
  `origin_quality: synthetic` and carries `origin_provenance` plus evidence IDs
  through the expected provenance object.
- `fixtures/golden/probabilistic/fixed-only.json` carries evidence IDs and a
  complete expected provenance shape, but its input says
  `origin_quality: observed` even though the fixture is a deterministic
  non-PHI golden fixture. This label should not be used to imply patient data.
- `fixtures/golden/shadow_trials/synthetic-demo-case.json` requires synthetic
  origin quality, `patient_evidence: false`, and a safety disclaimer. It points
  to the synthetic replay baseline.
- `web/lib/twin/replay/index.ts` attaches provenance and evidence IDs to every
  generated event and marks the timeline synthetic.

The manual baseline itself has no provenance or evidence fields. Provenance is
added by downstream extraction/state-building or replay/ensemble adapters, so
fixture presence alone is not proof of complete source lineage.

## Read-only verification evidence

Commands and observations:

```text
python fixture inventory/probe: PASS
  ECG normal: 2500 rows, 12 peaks, 72.0 bpm, 833.5 ms RR
  ECG fast:   2500 rows, 20 peaks, 120.0 bpm, 500.0 ms RR
  manual baseline: no provenance, AHA, timeline, ECG, or echo fields
  manual findings probe: 0 findings; AHA 17-segment model; imaging source none

node frontend fixture tests: 13 passed, 3 failed
  5 AHA/regional comparison tests passed
  5 provenance projection tests passed
  3 patient-report/snapshot tests failed in the existing direct harness:
    - two patient-report expectation mismatches
    - snapshot test blocked by Node strip-only parameter-property syntax
```

The frontend command was:

```bash
cd web
node --experimental-strip-types --loader ./tests/alias-loader.mjs --test \
  ./lib/twin/snapshots/__tests__/snapshots.test.ts \
  ./lib/twin/comparison/__tests__/provenance.test.ts \
  ./lib/twin/comparison/__tests__/regional.test.ts \
  ./lib/heart/__tests__/patient-report.test.ts
```

The failed frontend checks are recorded, not repaired, because this assignment
is limited to a read-only audit and one documentation file.

## Release disposition

**PARTIAL — synthetic demo only.**

The fixture inventory supports deterministic ECG analysis, echo metadata
parsing, longitudinal replay, AHA mapping, and provenance contracts in their
respective code/test paths. The canonical M10 demo seed does not exercise all
of them together, and its hash manifest omits the transitive synthetic replay
baseline. Do not claim that the seeded demo is an ECG/echo/AHA/longitudinal
integrated dataset until a future, explicitly authorized verification change
adds that coverage and reruns the relevant browser/API checks.

All artifacts remain synthetic and educational. They are not patient evidence
and must not be presented as diagnosis, treatment advice, or clinical
validation.
