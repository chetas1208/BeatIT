# M10.5 Agent 25 — Report and Provenance Verification

**Date:** 2026-09-26  
**Scope:** real API case and ensemble artifacts, physician-brief generation, artifact readback, and provenance limitations.  
**Disposition:** **PASS for isolated local artifact generation/readback; OPEN for the release report contract.**

This verification used synthetic, non-PHI inputs only. It does not establish
clinical validity or suitability for patient data.

## Exercise performed

The probe used the real FastAPI application with temporary SQLite and local
artifact-store paths. It performed this sequence:

1. `POST /api/v1/cases` created a case.
2. `POST /api/v1/cases/{case_id}/extract` loaded the reduced-function synthetic
   vitals from `fixtures/hearttwin/manual_reduced_function.json`.
3. `POST /api/v1/cases/{case_id}/operate` produced the persisted cardiac state.
4. `GET /api/v1/cases/{case_id}` read the operated case back.
5. `POST /api/v1/twin/ensemble` created an ensemble from
   `fixtures/golden/probabilistic/fixed-only.json`.
6. `GET /api/v1/twin/ensemble/{ensemble_id}` read the ensemble back.
7. `generate_physician_brief(...)` assembled a real `PHYSICIAN_BRIEF`
   `AssistantArtifact` from the persisted case and ensemble tool results.
8. The artifact was serialized, written to a temporary `LocalArtifactStore`,
   read back, and revalidated through `AssistantArtifact` and
   `DecisionSupportBundle`.

There is no dedicated FastAPI `/report` generation or report-readback route in
the current API. The physician-brief generator is therefore the implemented
backend report artifact boundary; the final unified report is currently a
frontend session-status surface.

## Verified results

| Check | Result | Evidence |
| --- | --- | --- |
| Case pipeline | PASS | Case reached `operated`; API readback contained 35 `source_map` entries. |
| Case safety boundary | PASS | `GET /api/v1/cases/{id}` included `safety_disclaimer`. |
| Ensemble generation | PASS | Real route returned an ensemble with 4 metric distributions. |
| Ensemble readback | PASS | Decoded `GET` payload exactly equaled the `POST` response. |
| Report generation | PASS | `generate_physician_brief` returned `type=physician_brief`. |
| Report schema round-trip | PASS | `AssistantArtifact` and `DecisionSupportBundle` both revalidated after JSON serialization. |
| Report artifact readback | PASS | Temporary `LocalArtifactStore` returned byte-identical serialized JSON. |
| Derived evidence | PASS | 1 reduced-function cardiac finding was present in `derived_evidence`. |
| Simulated results | PASS | 4 ensemble metric summaries were present in `simulated_results`. |
| Artifact provenance refs | PASS | 3 refs were present: `derived`, `simulated`, and `model_prior`. |
| Explicit limitations | PASS | Longitudinal, sensitivity, missing-evidence, conflict, and interpretation gaps were stated. |

The stable report payload (excluding generated artifact ID and timestamp) had
SHA-256:

```text
42f1fa78318158fe100037cf256d3d85204e4f29fb3c174990185f48abe2a87e
```

## Provenance findings

The API case state retained a detailed source ledger, but the generated report
did not expose it as observed evidence:

- API case state: **35** `source_map` entries.
- Physician brief: `observed_evidence=[]`.
- Report tools: `get_cardiac_findings`, `get_ensemble_distributions`, and
  `get_ensemble_assumptions`.
- The report classified the cardiac finding as derived and the ensemble output
  as simulated/model-prior data, which is consistent with the generator's
  implemented tool boundary.

This is an honest limitation, not a failed assertion: the current report tools
do not retrieve the case's raw `CardiacTwinState.source_map`. Consequently,
the report cannot bind each displayed finding or metric to an individual source
field, file, value, unit, and confidence record.

The artifact also carries provenance as a flat list of three references rather
than per-finding or per-metric references. The report's `missing_evidence`,
`conflicts`, and `possible_interpretations` lists are empty by contract, with
limitations explaining that those analyses are not implemented; empty does not
mean that no evidence is missing or that no conflicts exist.

The verifier supplied `synthetic_status="synthetic"` in the conversation
context, but the generated artifact did not retain that field. The ensemble
fixture's `origin_quality="observed"` was carried through unchanged even
though the exercise input is a repository synthetic fixture. The artifact
therefore must not be used by itself to claim real-world observation or
patient-data provenance.

## Safety and release boundary

The case and ensemble API responses carried their safety disclaimers. The
`AssistantArtifact` schema and generated physician-brief payload had no
top-level or payload `safety_disclaimer` field. The report does contain
nonclinical limitations, but this is not equivalent to the canonical API
disclaimer and should be resolved before exposing the artifact as a public
report contract.

The frontend `ReportSurface` remains a session completeness/readiness report:
it shows section status and selected IDs, but not the numerical EF/SV/CO values
or detailed per-field provenance. This agrees with the previously recorded
M10.5 wiring finding in `docs/release/AGENT_20_WIRING.md`.

## Validation command

The probe was run with temporary targets and no repository data writes:

```text
PYTHONPATH=. python <temporary Agent 25 API/report probe>
AGENT_25_REPORT_PROBE PASS
case_status=operated source_map_entries=35
case_disclaimer=True
ensemble_readback_exact=True
artifact_type=physician_brief derived_evidence=1 simulated_results=4
artifact_source_tools=3 provenance_refs=3
artifact_readback_exact=True
observed_evidence_empty=True
report_limitations_explicit=True
```

No production code, fixtures, databases, or existing runtime state were
modified by this contribution. Documentation hygiene validation:

```text
git diff --check -- docs/release/AGENT_25_REPORT.md
```

## Verdict

**PASS:** local report generation, schema validation, temporary artifact
write/readback, API ensemble readback, derived/simulated classification, and
explicit limitation reporting.

**OPEN / DO NOT SHIP as a complete report surface:** no report API route or
application-level report persistence contract; missing canonical disclaimer on
the assistant artifact; no raw source-map/per-field provenance in the report;
synthetic status is not retained; and the unified frontend REPORT surface does
not render numerical report values or detailed provenance.
