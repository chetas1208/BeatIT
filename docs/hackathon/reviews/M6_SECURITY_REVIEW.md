# M6 Shadow Trial Security and Safety Review

Reviewed: 2026-09-26 UTC  
Scope: Shadow Trial API error envelopes, safety-disclaimer propagation,
scenario text handling, CORS and storage boundaries, and privacy claims.  
Boundary: read-only implementation review plus this report. No implementation
files were changed.

## Gate verdict

**CONDITIONAL / NOT SAFE FOR PATIENT DATA.**

The M6 surface has several good local controls: typed Shadow Trial contracts,
re-validation of stored trial payloads before projection, parameterized SQLite
access, create-once trial IDs, restrictive local database permissions, and a
canonical disclaimer on successful responses and expected HTTP errors. The
deployment boundary is still trusted-demo-only. The API has no authentication,
authorization, tenant ownership, or rate limiting, and it accepts arbitrary
origins with credentials enabled. A paired result also contains complete
`CardiacTwinState` objects, which can include patient notes and CT payloads.
The disclaimer is a safety notice, not a privacy or access-control boundary.

## Findings

### 1. Wildcard credentialed CORS and unauthenticated trial access — HIGH, open

Evidence:

- `python/hearttwin/api.py:108-114` configures
  `allow_origins=["*"]`, `allow_credentials=True`, and all methods and
  headers.
- The M6 routes at `python/hearttwin/api.py:235-295` have no authentication,
  authorization, tenant, or ownership check. A caller who knows an ensemble or
  trial identifier can submit or retrieve data.
- A live preflight probe from this review returned:

  ```text
  cors_status=200
  cors_allow_origin=https://untrusted.example
  cors_allow_credentials=true
  ```

Impact: the current deployment permits cross-origin access from arbitrary
origins. There are no application cookies or bearer credentials in the M6
routes today, so this is not proof of an active authenticated-session theft;
it is nevertheless an unsafe default and would make a later authentication
addition vulnerable to cross-origin exposure unless CORS is tightened.

Disposition: acceptable only for synthetic, non-secret hackathon data behind a
deliberate trusted-demo boundary. Not acceptable for patient-data deployment.

### 2. Full cardiac state is persisted and returned — HIGH, open

Evidence:

- `python/hearttwin/ensemble.py:188-205` places the complete `CardiacTwinState`
  in every ensemble sample, and M6 copies those states into
  `PairedTwinResult` (`python/hearttwin/shadow_trial_contracts.py:194-206`).
- `CardiacTwinState` includes `patient_context`, `source_map`, warnings, and an
  optional arbitrary `ct_segmentation` object at
  `python/hearttwin/schemas.py:248-264`; patient notes are explicitly present
  at `python/hearttwin/schemas.py:99-105`.
- `_run_and_persist_shadow_trial` serializes the complete result at
  `python/hearttwin/api.py:217-221`, and the trial store writes the JSON payload
  without field minimization or encryption (`python/hearttwin/storage/shadow_trial_store.py:94-118`).
- The full result and individual pairs are then exposed by
  `GET /api/v1/shadow-trials/{trial_id}` and
  `GET /api/v1/shadow-trials/{trial_id}/pairs/{sample_id}`.

Impact: a safety disclaimer does not prevent raw notes, source metadata,
imaging metadata, or other identifiers from being persisted and returned. The
M6 store has no retention, deletion, encryption-at-rest, or de-identification
policy. Do not send identifiable or clinical records to this surface.

### 3. Scenario labels and descriptions bypass the safety classifier — MEDIUM,
open

Evidence:

- `ScenarioDefinition.label` and `.description` are accepted as unconstrained
  strings (`python/hearttwin/shadow_trial_contracts.py:92-109`). There are no
  maximum lengths, content policy, or call to `check_request_safety`.
- The engine explicitly treats them as inert metadata and excludes them from
  numerical evaluation (`python/hearttwin/shadow_trial_engine.py:123-143,263-268`).
  This is a positive prompt-injection containment property for the math path,
  but it is not a user-facing safety-language control.
- A direct contract probe accepted:

  ```text
  label=diagnosis: take this medication
  description=clinical treatment recommendation
  ```

- The frontend renders ordinary React text and no `dangerouslySetInnerHTML` was
  found in the scoped Shadow Trial component, so this review found no direct
  HTML injection path. That does not make clinical or treatment wording safe
  to persist or display.

Impact: a caller can attach diagnostic, treatment, or other misleading claims
to a hypothetical experiment while the response retains the canonical
disclaimer. Unbounded text and arbitrary provenance dictionaries also create a
payload-size and audit-noise risk. The numeric engine does not consume these
fields, but the metadata can still influence human interpretation.

### 4. Expected M6 error envelopes carry the disclaimer; unexpected 500s do not —
MEDIUM, open

Positive evidence:

- M6 `HTTPException` and request-validation handlers at
  `python/hearttwin/api.py:1175-1197` add the canonical disclaimer to
  Shadow Trial 404, 422, and 503 responses.
- The success response and typed effects/pair projections carry and validate
  the same disclaimer (`python/hearttwin/api.py:252-295` and
  `python/hearttwin/shadow_trial_contracts.py:312-388`).
- Direct probes returned the disclaimer for malformed creation input and a
  missing trial:

  ```text
  validation_status=422; validation_disclaimer_ok=True
  not_found_status=404; not_found_disclaimer_ok=True
  ```

Gap:

- The routes catch known `ShadowTrialStoreError`, `OSError`, and `ValueError`
  cases, but there is no M6-specific catch-all handler around unexpected
  failures (`python/hearttwin/api.py:235-249,252-295`). A probe that injected a
  synthetic unexpected `RuntimeError` produced:

  ```text
  status=500
  content_type=text/plain; charset=utf-8
  body=Internal Server Error
  disclaimer_present=False
  ```

Impact: the normal safety envelope is reliable for modeled errors, but not a
universal API invariant. Clients must not assume every M6 failure is JSON or
contains `safety_disclaimer`.

### 5. Local storage controls are useful but do not establish integrity or
privacy — MEDIUM, bounded

Positive evidence:

- `SQLiteShadowTrialStore` rejects `:memory:`, creates its parent directory as
  `0700`, and attempts to set the database to `0600`
  (`python/hearttwin/storage/shadow_trial_store.py:59-73`). The repository
  database was observed as mode `0600` under a mode `0700` `data` directory.
- Writes use parameterized SQL and create-once semantics; an exact replay is
  idempotent and a conflicting payload is rejected
  (`python/hearttwin/storage/shadow_trial_store.py:94-118`).
- Reads validate the persisted object with `ShadowTrialResult` before exposing
  a projection (`python/hearttwin/api.py:224-232`). Malformed persisted data is
  mapped to a 503 rather than returned as an unchecked object.

Limitations:

- There is no encryption at rest, key management, retention/deletion policy,
  backup access policy, or multi-tenant isolation.
- The immutable trial store does not cryptographically recompute and verify
  the trial ID or fingerprint. Pydantic shape validation is not tamper
  detection.
- The baseline ensemble store remains replaceable by ensemble ID. M6 retains
  the baseline state in the trial result, but the provenance ID alone is not a
  content-addressed or authenticated snapshot proof.

These controls support a local trusted demo, not a security or privacy claim
for a hosted clinical workload.

### 6. Privacy and provenance claims remain caller-trusted — MEDIUM, open

Evidence:

- M6 copies `origin_provenance` and `evidence_ids` from the persisted ensemble
  into trial provenance (`python/hearttwin/shadow_trial_engine.py:250-269`).
- The fields are typed as `list[dict[str, Any]]` and `list[str]`, not as a
  privacy-reviewed or de-identified schema
  (`python/hearttwin/shadow_trial_contracts.py:112-134`).
- No M6 route applies `redact_pii`, and no field-level allowlist removes notes,
  filenames, source records, or imaging metadata before storage or response.
- `origin_quality` and synthetic lineage are validated as labels, but caller
  supplied provenance is not independently authenticated. A label such as
  `observed` is a lineage assertion, not proof of observation.

Impact: the implementation can preserve useful audit lineage, but it must not
be described as de-identified, HIPAA-safe, clinically private, or independently
verified. Synthetic fixtures are the only safe current deployment assumption.

## Verified passes and non-findings

- Same-sample pairing and no-resampling are numerical design properties; this
  review found no scenario text path into the evaluator.
- SQL parameters are used for trial IDs and payloads; no SQL injection path was
  identified in the scoped store.
- Stored trial payloads are not returned blindly: the API re-validates them
  before effects, pair, or full-result projection.
- Normal successful responses and modeled 404/422/503 failures carry the exact
  canonical educational disclaimer.
- No direct XSS sink was found in the scoped Shadow Trial React component; text
  is rendered as React text rather than injected HTML. Browser-level security
  testing was not performed.

## Verification record

Read-only checks performed:

```text
GET/POST TestClient probes:
  modeled validation error: 422, safety disclaimer present
  missing trial: 404, safety disclaimer present
  arbitrary-origin CORS preflight: 200, origin reflected, credentials=true
  unexpected RuntimeError probe: 500 text/plain, disclaimer absent
  scenario text probe: diagnostic/treatment text accepted by contract

Static inspection:
  M6 routes, contracts, engine, SQLite store, CardiacTwinState, safety module,
  frontend ShadowTrialPanel, and existing M6 review/test documents
```

No implementation files, tests, configuration, or data records were edited by
this review.

## Release disposition

Keep M6 **conditional and demo-only**. Before accepting any patient or
identifiable data, the minimum security work is:

1. Add authentication, authorization/ownership checks, tenant isolation, and
   rate limiting to all Shadow Trial create/read routes.
2. Restrict CORS to explicit trusted origins and do not enable credentials
   unless a concrete authenticated browser flow requires them.
3. Minimize the trial payload to numerical fields and audited lineage; omit
   patient notes, CT payloads, raw source records, and other non-required data.
4. Add scenario text validation/length limits and preserve non-clinical display
   language across API and UI surfaces.
5. Define encryption, retention, deletion, backup, and access-audit policies.
6. Add a consistent JSON catch-all error envelope for M6 failures, including
   the disclaimer, without exposing internal exception details.
7. Bind trial identity to a verified content digest and establish an immutable,
   authenticated baseline snapshot rather than relying on IDs and caller labels.

