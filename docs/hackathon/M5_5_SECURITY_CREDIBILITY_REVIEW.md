# M5.5 Security, Privacy, and Credibility Review

Reviewed: 2026-09-26 UTC  
Scope: ensemble persistence/API responses, logging/tracing, secrets, PII/raw
payload handling, public claims, version metadata, and known limitations.  
Boundary: read-only review plus this isolated report. M6, M7, and M8 were not
started.

## Gate verdict

**CONDITIONAL / NOT SAFE FOR PATIENT DATA.**

The canonical ensemble contract has strong local controls: parameterized SQLite
writes, restrictive local file permissions, an exact mandatory safety disclaimer,
explicit synthetic lineage, versioned model metadata, and no live secret pattern
was found in the scoped repository scan. However, the deployed HTTP surface has
no authentication or authorization and enables credentialed CORS for arbitrary
origins. The ensemble response and local record also preserve the full
`CardiacTwinState`, including optional patient notes and CT payload fields. That
combination is an exposure risk if non-synthetic or identifiable data reaches the
API. The current evidence supports synthetic/demo use only, not a privacy-safe
clinical deployment.

## Findings

### 1. HTTP access control and CORS — HIGH, open

Evidence:

- `python/hearttwin/api.py:95-101` configures `allow_origins=["*"]`,
  `allow_credentials=True`, and all methods/headers.
- The ensemble routes at `python/hearttwin/api.py:156-195` have no auth
  dependency, API-key check, tenant check, or case-owner check.
- Case and trace routes at `python/hearttwin/api.py:555-581` and
  `:599-616` likewise accept a caller-supplied ID without authorization.
- A live preflight probe returned:

  ```text
  cors_preflight_status= 200
  allow_origin= https://attacker.example
  allow_credentials= true
  ```

Impact: a browser origin outside the trusted deployment can make credentialed
cross-origin requests. With a known case or ensemble ID, the caller can read
the corresponding response. This is acceptable only for synthetic, non-secret
hackathon data behind an explicit deployment boundary; it is not an acceptable
production privacy posture.

### 2. Ensemble data minimization — HIGH, open

Evidence:

- `python/hearttwin/schemas.py:248-264` defines `CardiacTwinState` with
  `patient_context`, `source_map`, warnings, and optional `ct_segmentation`.
- `python/hearttwin/ensemble.py:436-458` validates and returns each sampled
  state as part of the ensemble response.
- `python/hearttwin/storage/ensemble_store.py:88-115` persists the complete
  response JSON without field-level minimization or encryption.
- A temporary-database API probe posted sentinel values in
  `state.patient_context.notes` and `state.ct_segmentation`; the response
  returned both values:

  ```text
  post_status= 200
  full_response_contains_patient_note= True
  full_response_contains_ct_payload= True
  safety_disclaimer_exact= True
  ```

Impact: the disclaimer and lineage metadata do not prevent raw or identifiable
state fields from being returned or persisted. The ensemble API should receive
and return only the fields required for the sampled projection, or must be
protected by an authenticated, authorized data boundary before real data is
allowed.

### 3. Trace sanitization is best-effort, not de-identification — MEDIUM, open

Positive controls:

- `python/hearttwin/tools/weave_trace.py:20-36` has a denylist for common PII
  keys, including names, email, phone, MRN, SSN, raw text, and uploaded bytes.
- `:291-324` recursively trims lists, limits strings to 280 characters, redacts
  obvious SSN/email/date/long-ID patterns, and replaces bytes with a size marker.
- `:327-335` records upload metadata rather than file bytes.
- Existing tests cover obvious PII/raw-report trimming and secret absence in
  `python/hearttwin/tests/test_weave_trace_fallback.py:22-33` and
  `python/hearttwin/tests/test_weave_integration.py:105-125`.

Gaps:

- `:297-309` redacts only exact denylisted key names; fields such as
  `patient_context.notes`, `evidence`, arbitrary provenance dictionaries, and
  domain-specific identifiers are not generally classified as sensitive.
- `:327-335` preserves `filename`; a filename can contain a patient name or
  encounter identifier.
- `:48-69`, `:211-224`, and the API trace routes return raw `case_id`/trace
  identity metadata. Case IDs are not necessarily PHI, but no guarantee is
  enforced that they are opaque non-identifying IDs.
- `python/hearttwin/api.py:563-581` and `:619-670` expose locally retained
  trace payloads over unauthenticated HTTP/SSE.

Conclusion: the sanitizer reduces accidental leakage but is not a complete PHI
boundary. Do not describe Weave/local traces as de-identified storage based on
these controls alone.

### 4. Local persistence — PASS within a narrow boundary

Evidence:

- `python/hearttwin/storage/ensemble_store.py:61-76` rejects `:memory:`,
  creates the parent directory with mode `0700`, and sets the database file to
  `0600` where supported.
- `:95-115` serializes before the transaction and uses parameterized SQLite
  values plus an atomic upsert.
- `:117-138` maps SQLite errors and malformed JSON to `EnsembleStoreError`.
- The focused store probe returned:

  ```text
  db_mode= 0o600
  parent_mode= 0o700
  ```

Limit: this protects a local file from ordinary same-host users; it does not
provide encryption at rest, retention/deletion policy, multi-worker durability,
or API authorization. `docs/hackathon/M5_5_COMPLETION.md:58-59` and
`docs/credibility/beatit-model-manifest.json:30-35` correctly state the shared
persistent-filesystem limitation.

### 5. Secrets — PASS for the scoped source tree; verification tooling has a
false-positive gate failure

Evidence:

- `.gitignore:15-18,35-38,65-73` excludes `.env`, local credentials, key files,
  raw uploads, artifacts, and the default ensemble database.
- `.env.example:13,29,35-36,61,67,81` and `web/.env.example:17,26` contain
  placeholders or empty values, not live credentials.
- A repository secret-pattern scan excluding generated/dependency/data artifacts
  produced no matches. The only key-like strings found by follow-up inspection
  were intentional fake values in tests at
  `python/hearttwin/tests/test_weave_integration.py:119` and
  `python/hearttwin/tests/careguard/test_careguard_config_security.py:26`.
- `python/hearttwin/api.py:272-293` has a response secret scan, and its probe
  returned `leaked_names= []` for configured sentinel secrets.
- `python/hearttwin/api.py:203-238` exposes configuration booleans/metadata,
  not secret values.

The narrow environment verification command did **not** pass:

```text
ERRORS:
  - .env.example: MODEL_API_KEY appears to contain a real secret value
  - .env.example: OPENAI_API_KEY appears to contain a real secret value
RESULT: FAILED
```

This is a verifier defect/false positive: `scripts/verify_env.py:62-65` treats
any non-empty `API_KEY`/`TOKEN` placeholder longer than 24 characters as secret,
while the values are explicitly `REPLACE_WITH_*` placeholders. It is not
evidence of a committed live secret, but it weakens the credibility gate until
the verifier recognizes placeholders. No production file was changed in this
review.

### 6. Safety and clinical/FDA credibility — mostly PASS, one wording risk

Positive evidence:

- `python/hearttwin/safety.py:12-17` defines the canonical educational,
  non-diagnostic, non-treatment, non-medical-device disclaimer.
- `python/hearttwin/ensemble.py:279-280` requires the exact canonical disclaimer
  in `EnsembleResponse`; `:447-452` emits it and adds an educational warning.
- `python/hearttwin/ensemble.py:105-109` rejects synthetic replay provenance
  labeled `observed`.
- `docs/credibility/beatit-model-manifest.json:41-47` explicitly lists
  unsupported claims: diagnosis, treatment recommendation, patient-specific
  probability, clinical confidence interval, Bayesian posterior, and calibrated
  risk.
- `docs/hackathon/OBSERVED_SYNTHETIC_POLICY.md:40-50` and
  `Decisions.md:16-20` preserve the same boundary.
- `docs/hackathon/M5_5_COMPLETION.md:7-10,52-63` honestly marks M5.5
  incomplete and records the non-clinical/local-persistence limitations.

Credibility risk:

- `docs/research.md:119-126` says “DualBeat follows FDA guidance” and states
  there is a “required disclaimer.” A repository disclaimer and safety tests do
  not establish regulatory compliance or legal applicability. This wording
  should be treated as an unsupported regulatory-position claim unless reviewed
  by an appropriate regulatory/legal owner.
- `README.md:28-29,47-51` uses “clinical readout,” “for radiologists &
  cardiologists,” and “clinical AI pipeline” language. The surrounding text
  gives strong educational disclaimers, but these phrases can still imply a
  clinical-use validation level that the M5.5 manifest expressly disclaims.

No M5.5 ensemble evidence supports clinical calibration, patient-specific
probabilities, FDA clearance, diagnostic performance, or treatment efficacy.

### 7. Version metadata and manifest consistency — PASS with incomplete status

Evidence:

- `pyproject.toml:5-8`, `package.json:1-4`, and `python/hearttwin/api.py:87-93`
  consistently identify the software as version `0.1.0`.
- `docs/credibility/beatit-model-manifest.json:3-21` identifies
  `m5.5-ensemble-projection-v1`, `m5.5-backend-ensemble-v1`, `m5-priors-v1`,
  and `m5.5-golden-v1`.
- `models/manifest.json:1-23` is metadata-only and records that the optional
  VISTA-3D checkpoint is not loaded at startup.
- Both manifests parse as valid JSON in the narrow check.

The manifest status is `m5.5-in-progress` and the completion record is
`INCOMPLETE`; neither should be promoted to a completed or clinically validated
release claim. The deployment document still describes a Vercel Python backend
(`docs/deployment-vercel.md:5-15`), while local SQLite durability requires
persistent shared storage. That deployment/documentation mismatch must remain a
release limitation, not be presented as production persistence.

## Narrow verification run

Commands and results:

```text
PYTHONPATH=. uv run --project . --extra dev pytest -q \
  python/hearttwin/tests/test_ensemble_api.py \
  python/hearttwin/tests/test_ensemble_store.py \
  python/hearttwin/tests/test_weave_trace_fallback.py \
  python/hearttwin/tests/test_weave_integration.py \
  python/hearttwin/tests/test_safety_language.py
61 passed, 1 skipped
```

Additional checks:

- Secret-pattern scan: no live-key/private-key matches in the scoped source
  tree.
- Temporary persistence permission probe: database `0600`, parent `0700`.
- Manifest JSON validation: both manifests valid.
- API secret-response probe: `leaked_names= []`.
- API exposure probe: patient-note and CT-payload sentinels were returned in
  ensemble samples.
- CORS preflight probe: arbitrary origin accepted with credentials.
- `PYTHONPATH=. uv run --project . python scripts/verify_env.py`: **failed only
  on the placeholder false positives documented above**.

## Release disposition and bounded next actions

M5.5 should remain **incomplete/conditional** for this gate. Within the current
scope, the minimum release actions are:

1. Do not send patient or identifiable data to the unauthenticated, wildcard-CORS
   deployment; use synthetic fixtures only.
2. Before any real-data deployment, add authentication/authorization and
   restrict CORS to explicit trusted origins.
3. Minimize or omit patient notes, CT payloads, and other non-required state from
   ensemble samples and persisted records; define retention/deletion behavior.
4. Tighten trace sanitization for filenames, notes, provenance/evidence fields,
   and identifiers, or document a formal de-identification boundary.
5. Correct the env verifier placeholder heuristic and replace the FDA wording
   with a non-regulatory description unless formally reviewed.

These are security/credibility follow-ups only. No M6, M7, or M8 work was
performed.
