# Agent 09 — synthetic-cohort FHIR validation

**Date:** 2026-09-26 UTC
**Scope:** Read-only validation of the existing 500-profile cohort under
`data/synthetic_cohort_500/`, with emphasis on FHIR-shaped bundles, intra-bundle
references, and synthetic provenance.
**Change boundary:** Only this report was written. Production code and generated
cohort data were not edited or regenerated. No environment-variable values,
credentials, or uploaded content were printed.

## Plan

1. Inspect the generator, repository verifier, bundle validator, manifest, and
   generated directory layout.
2. Reopen all 500 generated bundles and run the repository's `validate_bundle`
   validator.
3. Independently check bundle identity, resource shape, `subject`/`patient`/
   `encounter` references, FHIR metadata tags, and the matching profile's
   provenance fields.
4. Run the existing no-regeneration cohort verifier and record limitations of
   the structural validator and the synthetic dataset.

## Generator and artifact contract

The generator is deterministic with seed `20260926` and creates profile IDs
`BEATIT-SYN-0001` through `BEATIT-SYN-0500`. Its FHIR output is explicitly
described as **FHIR R4-shaped**, not as a complete clinical FHIR implementation
([`build_cohort_500.py`](../../../scripts/build_cohort_500.py#L1-L8)). Each bundle
is a `collection` containing one `Patient`, one `Encounter`, and six `Observation`
resources ([bundle construction](../../../scripts/build_cohort_500.py#L94-L124)).

The generator invokes `validate_bundle` for every generated bundle and aborts if
fewer than 500 are reported valid ([generation gate](../../../scripts/build_cohort_500.py#L262-L283)).
It also records the bundle path in each profile and writes the manifest, QA files,
and checksums ([metadata and checksums](../../../scripts/build_cohort_500.py#L305-L340)).

## Executable validation

Run from the repository root. This command is read-only: it parses existing JSON
files and does not call the generator or write output.

```bash
python - <<'PY'
import json
from collections import Counter
from pathlib import Path

from python.hearttwin.careguard.fhir.bundle_validator import validate_bundle

root = Path("data/synthetic_cohort_500")
fhir_paths = sorted((root / "fhir").glob("BEATIT-SYN-*.json"))
profile_paths = sorted((root / "profiles").glob("BEATIT-SYN-*.json"))
manifest = json.loads((root / "manifest.json").read_text())

expected_ids = {f"BEATIT-SYN-{i:04d}" for i in range(1, 501)}
seen_ids = {path.stem for path in fhir_paths}
valid = 0
issues = 0
warnings = 0
reference_failures = 0
tag_failures = 0
profile_failures = 0
shape_failures = 0
unsupported = Counter()
resource_counts = Counter()

if len(fhir_paths) != 500 or seen_ids != expected_ids:
    raise SystemExit("FHIR file/count/ID check failed")
if len(profile_paths) != 500:
    raise SystemExit("profile file count check failed")

for path in fhir_paths:
    bundle = json.loads(path.read_text())
    summary = validate_bundle(bundle)
    valid += int(summary.valid)
    issues += len(summary.issues)
    warnings += len(summary.warnings)
    unsupported.update(item["resourceType"] for item in summary.unsupported)
    resource_counts.update(summary.resource_counts)

    entries = [entry.get("resource", {}) for entry in bundle.get("entry", [])]
    refs = {(resource.get("resourceType"), resource.get("id")) for resource in entries}
    expected_bundle_id = f"bundle-{path.stem.lower()}"
    if (bundle.get("resourceType"), bundle.get("type"), bundle.get("id")) != (
        "Bundle", "collection", expected_bundle_id
    ) or len(entries) != 8:
        shape_failures += 1

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if entry.get("fullUrl") != f"urn:uuid:{resource.get('id')}":
            shape_failures += 1
        for field in ("subject", "patient", "encounter"):
            reference = (resource.get(field) or {}).get("reference")
            if reference and "/" in reference and not reference.startswith("urn:"):
                kind, identifier = reference.split("/", 1)
                if (kind, identifier) not in refs:
                    reference_failures += 1

    tags = (bundle.get("meta") or {}).get("tag", [])
    if not any(
        tag.get("system") == "https://hearttwin.local/careguard"
        and tag.get("code") == "synthetic_demo"
        for tag in tags
    ):
        tag_failures += 1

for path in profile_paths:
    profile = json.loads(path.read_text())
    provenance = profile.get("provenance") or {}
    if not (
        profile.get("synthetic") is True
        and provenance.get("source_type") == "synthetic"
        and provenance.get("identity_policy") == "not derived from a real person"
        and "synthetic_demo" in profile.get("phenotype_tags", [])
        and "deterministic" in profile.get("phenotype_tags", [])
        and profile.get("fhir_path") == f"fhir/{path.name}"
    ):
        profile_failures += 1

checks = {
    "FHIR_BUNDLES": len(fhir_paths) == 500,
    "PROFILES": len(profile_paths) == 500,
    "FHIR_VALID": valid == 500,
    "VALIDATOR_ISSUES": issues == 0,
    "VALIDATOR_WARNINGS": warnings == 0,
    "REFERENCES": reference_failures == 0,
    "BUNDLE_SHAPE": shape_failures == 0,
    "PROVENANCE_TAGS": tag_failures == 0,
    "PROFILE_PROVENANCE": profile_failures == 0,
    "UNSUPPORTED_RESOURCES": not unsupported,
    "MANIFEST_COUNTS": all(
        manifest.get(key) == expected
        for key, expected in {
            "profile_count": 500,
            "unique_profile_count": 500,
            "fhir_valid": 500,
        }.items()
    ),
}
for name, passed in checks.items():
    print(f"{name:<24} {'PASS' if passed else 'FAIL'}")
print("RESOURCE_COUNTS", dict(sorted(resource_counts.items())))
if not all(checks.values()):
    raise SystemExit("FHIR cohort validation failed")
PY
```

Observed output on 2026-09-26:

```text
FHIR_BUNDLES             PASS
PROFILES                 PASS
FHIR_VALID               PASS
VALIDATOR_ISSUES         PASS
VALIDATOR_WARNINGS       PASS
REFERENCES               PASS
BUNDLE_SHAPE             PASS
PROVENANCE_TAGS          PASS
PROFILE_PROVENANCE       PASS
UNSUPPORTED_RESOURCES    PASS
MANIFEST_COUNTS          PASS
RESOURCE_COUNTS {'Encounter': 500, 'Observation': 3000, 'Patient': 500}
```

The repository's broader no-regeneration check was also run:

```bash
python scripts/verify_cohort_500.py
```

It returned `PASS` for profiles, unique IDs, synthetic flag, manifest count,
FHIR count, ingestion, database persistence, restart readback, provenance,
physiological invariants, and checksums, followed by `COHORT READY`. The verifier
is useful cohort-integrity evidence, but its FHIR check compares the manifest's
`fhir_valid` value; the direct command above is the check that reopens and
validates all bundle files ([verifier](../../../scripts/verify_cohort_500.py#L27-L96)).

## Evidence summary

| Check | Result |
|---|---:|
| FHIR bundle files | 500 |
| Profile files and unique IDs | 500 / 500 |
| Bundles accepted by `validate_bundle` | 500 / 500 |
| Bundle entries | 8 in every bundle |
| Resource totals | 500 Patient, 500 Encounter, 3,000 Observation |
| Structural validator issues/warnings | 0 / 0 |
| Unresolved checked references | 0 |
| Missing `synthetic_demo` FHIR tags | 0 |
| Profile provenance failures | 0 |
| Unsupported resource types | 0 |
| Longitudinal profiles | 250 |
| Synthetic ECG profiles | 166 |

The generated metadata records the same 500-profile/500-FHIR-valid result, seed,
category counts, and source references ([manifest](../../../data/synthetic_cohort_500/manifest.json#L1-L29)).
Every profile has `synthetic: true`, `source_type: "synthetic"`, the identity
policy `not derived from a real person`, and `synthetic_demo` plus `deterministic`
phenotype tags ([profile construction](../../../scripts/build_cohort_500.py#L172-L189)).
Every bundle carries this tag:

```text
system = https://hearttwin.local/careguard
code   = synthetic_demo
```

The manifest's `source_references` are deliberately local and descriptive:
`synthetic local generator` and `FHIR R4-shaped bundle contract`. They are not
external clinical data sources or terminology references.

## References and provenance interpretation

- Each `Encounter.subject` points to the bundle's Patient.
- Each Observation has a `subject` pointing to that Patient and an `encounter`
  pointing to that Encounter.
- Resource IDs are unique within each bundle, and each entry's `fullUrl` is the
  corresponding `urn:uuid:` form of its resource ID.
- The bundle-level `meta.tag` and profile-level provenance fields classify the
  artifacts as synthetic demo data; they are not a claim that the values are
  clinically measured.
- The generator's exclusion policy is explicit: it does not mix identities from
  Synthea, PTB-XL, NHANES, or another source ([generator docstring](../../../scripts/build_cohort_500.py#L1-L8)).
- The data is not a FHIR `Provenance` resource. Provenance is represented by the
  bundle tag, profile JSON, manifest, and checksums.

## Validator scope and limitations

`validate_bundle` is a repository-local structural validator. It checks that the
top-level value is a Bundle, records resource IDs and duplicates, recognizes the
supported resource-type list, checks selected status fields, checks for a Patient,
and warns on unresolved `subject`, `patient`, or `encounter` references
([validator](../../../python/hearttwin/careguard/fhir/bundle_validator.py#L31-L100)).
The report command treats both validator issues and warnings as failures.

This does **not** establish full FHIR R4 conformance. Specifically:

- No official FHIR JSON schema, profile validator, terminology server, or
  conformance test suite was run.
- The local validator does not validate every cardinality, datatype, binding,
  invariant, or reference-bearing field. It also reports some content problems as
  issues/warnings without changing its `valid` flag; the report's explicit zero
  issue/warning gate compensates for that behavior on this cohort.
- The six observation codes use the local synthetic system
  `https://beatit.local/synthetic`; they are not asserted LOINC/SNOMED/UCUM
  mappings. Units are lightweight strings such as `beats/min`, `mm[Hg]`, `mL`,
  and `%`.
- The bundles are small `collection` bundles with synthetic scalar observations,
  not clinical documents, transactions, longitudinal FHIR histories, or evidence
  of real-world patient identity.
- The dataset is deterministic and useful for parser, reference, provenance, and
  pipeline tests. It is not representative clinical data and does not validate
  clinical plausibility, diagnostic performance, treatment safety, or deployment
  readiness.
- The optional ECG files are generated waveform fixtures; their presence does
  not make the FHIR bundles contain an `Observation` waveform or establish a
  clinical ECG interpretation.

## Disposition

**PASS — read-only structural/reference/provenance validation of all 500 generated
bundles.**

**LIMITED — not a full FHIR R4 conformance certification and not clinical-data
validation.** Any external exchange or clinical-use claim requires a separate
profile/schema/terminology validation, data-governance review, and safety review.
