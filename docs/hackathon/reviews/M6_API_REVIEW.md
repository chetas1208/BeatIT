# M6 API Contract and Safety Review

Date: 2026-09-26  
Scope: the implemented M6 Shadow Trial HTTP routes, Pydantic request/result
contracts, persistence/error mapping, safety disclaimer behavior, and the
frontend wire types. This is a read-only implementation review; no
implementation files were changed. M7 Split Heart, M8 Missing Piece, and
frontend redesign are out of scope.

## Verdict

**FAIL for the API safety/contract gate.** The successful Shadow Trial path is
functional and the focused tests cover creation, retrieval, paired results,
validation, idempotent persistence, and store failure mapping. However, the
API does not preserve the mandatory `safety_disclaimer` on ordinary 4xx error
responses, and two read endpoints are not represented by typed response
contracts in OpenAPI. There is also a safety boundary gap for client-supplied
scenario text and an integrity gap in the optional scenario baseline metadata.

The findings below are based on the current workspace, not on a proposed
implementation.

## Route contract matrix

| Route | Success shape | Implemented error mapping | Review result |
| --- | --- | --- | --- |
| `POST /api/v1/shadow-trials` | `ShadowTrialResult`, response model | missing baseline `404`; invalid engine/scenario `422`; persistence `503` | Success path passes; error safety envelope fails |
| `GET /api/v1/shadow-trials/{trial_id}` | `ShadowTrialResult`, response model | missing trial `404`; persistence `503` | Success path passes; error safety envelope fails |
| `GET /api/v1/shadow-trials/{trial_id}/effects` | Untyped `dict[str, Any]` summary | missing trial `404`; persistence `503` | Functional response; schema/documentation fails |
| `GET /api/v1/shadow-trials/{trial_id}/pairs/{sample_id}` | Untyped `dict[str, Any]` pair envelope | missing trial/pair `404`; persistence `503` | Functional response; schema/documentation fails |

The two untyped response descriptions above reflect the implementation: these
routes have no `response_model`, so OpenAPI describes them as generic objects.

## Passing checks

### Request and scenario validation — PASS with integrity caveats

The request contract uses `extra="forbid"`, requires a non-empty baseline
ensemble ID, restricts metrics to the declared metric literal, rejects empty
or duplicate metric lists, and rejects duplicate scenario parameters
(`python/hearttwin/shadow_trial_contracts.py:72-109` and `174-190`). Parameter
values must be finite, and a supplied `delta` must equal `value - baseline`.
The engine additionally rejects unknown parameters, out-of-range values, and
wrong units (`python/hearttwin/shadow_trial_engine.py:87-111`).

The focused route test proves the main mappings:

- absent baseline ensemble -> `404`;
- out-of-bounds `afterload_index` -> `422`;
- persistence failure -> `503`;
- missing trial and missing pair -> `404`.

### Successful response safety — PASS

The successful create, full retrieval, effects, and pair tests all assert the
canonical disclaimer. `ShadowTrialResult` also rejects a non-canonical
disclaimer at `python/hearttwin/shadow_trial_contracts.py:331-334`. The engine
uses hypothetical/simulated language and explicitly warns that results are
not diagnosis, treatment advice, or clinical efficacy evidence
(`python/hearttwin/shadow_trial_engine.py:265-270`).

### Persistence and replay — PASS for the tested path

The API retrieves the baseline through the durable ensemble store, persists the
trial through the file-backed Shadow Trial store, and accepts exact repeated
writes while rejecting a changed payload for an existing trial ID. The route
test covers exact repeated-create idempotence and maps a `ShadowTrialStoreError`
to `503`.

## Findings requiring remediation

### F-01 / P0 — Error responses omit the mandatory safety disclaimer

The M6 API returns the disclaimer on successful payloads but not on normal
validation or resource errors. The only custom exception handler in
`python/hearttwin/api.py` is for `SafetyViolation` (`api.py:1140-1148`); there
is no handler for FastAPI `RequestValidationError` or the app's
`HTTPException` responses.

Direct live probes against `TestClient(app)` produced:

```text
POST /api/v1/shadow-trials with missing scenario
422 {'detail': [...]}                         safety_disclaimer: absent

POST /api/v1/shadow-trials with unknown metric
422 {'detail': [...]}                         safety_disclaimer: absent

POST /api/v1/shadow-trials with malformed JSON
422 {'detail': [...]}                         safety_disclaimer: absent

GET /api/v1/shadow-trials/nope
404 {'detail': 'Shadow Trial not found'}      safety_disclaimer: absent

GET /api/v1/shadow-trials/nope/effects
404 {'detail': 'Shadow Trial not found'}      safety_disclaimer: absent

GET /api/v1/shadow-trials/nope/pairs/sample-0
404 {'detail': 'Shadow Trial not found'}      safety_disclaimer: absent
```

The existing tests encode the same problem by asserting exact error bodies
without a disclaimer at `python/hearttwin/tests/test_shadow_trial_api.py:82-116`
and `:137-162`. This is not just a documentation issue: the frontend's
`ApiRequestError` makes `safetyDisclaimer` optional, so callers cannot rely on
the safety boundary being present when a request fails.

Required remediation: standardize all M6 errors, including FastAPI body
validation, `HTTPException` 404/503 responses, and unexpected internal errors,
on an envelope containing at least `detail` (or a stable error code) and the
canonical `safety_disclaimer`. Add regression tests for malformed JSON,
missing fields, missing resources, and persistence failure.

### F-02 / P1 — Effects and pair response contracts are untyped and incomplete in OpenAPI

`GET /effects` and `GET /pairs/{sample_id}` return raw dictionaries at
`python/hearttwin/api.py:231-261` without `response_model` declarations. A
read-only `app.openapi()` inspection reported:

```text
/api/v1/shadow-trials/{trial_id}/effects
  responses = ['200', '422']
  200 schema = type object, additionalProperties true

/api/v1/shadow-trials/{trial_id}/pairs/{sample_id}
  responses = ['200', '422']
  200 schema = type object, additionalProperties true
```

The same OpenAPI inspection showed that the documented response keys omit the
implemented `404` and `503` cases for all four routes. This leaves clients
without a machine-readable contract for the effect summary, pair envelope, or
service failure behavior. The frontend TypeScript types cover the pair route
but do not model the effects route, and `ShadowTrialResponse` does not include
the backend's optional `definition` field (`web/types/shadow-trial.ts:64-78`).

Required remediation: add explicit response models for the effects summary,
pair envelope, and common error envelope; declare `404`, `422`, and `503`
responses in OpenAPI; and reconcile the TypeScript wire types with the actual
backend response. Keep the summary route intentionally compact, but make its
fields explicit.

### F-03 / P1 — Free-form scenario text bypasses the safety checker

`ScenarioDefinition.label` and `.description` are arbitrary non-empty strings
with no safety validation (`shadow_trial_contracts.py:92-102`). The M6 route
passes the request directly into `run_shadow_trial` (`api.py:207-228`); it does
not call `check_request_safety` or otherwise constrain these fields before they
are persisted and returned to the UI.

A direct contract/engine probe with the existing golden ensemble was accepted
and echoed unchanged:

```text
label       = "Treatment recommendation"
description = "This treatment will work"
accepted    = True
```

This permits unsafe clinical language to enter a persisted M6 definition and
the frontend's provenance/details display, even though the numerical output
has a disclaimer. The probe did not claim an HTTP success run; it demonstrates
that the route's request model and delegated engine do not enforce the safety
boundary.

Required remediation: either restrict scenario labels/descriptions to
server-generated safe labels, or run the established safety checker on all
client-supplied scenario text and return the canonical safety error envelope
when blocked. Add tests for diagnosis, treatment, medication, and emergency
language in both label and description.

### F-04 / P1 — Declared scenario baseline metadata is not semantically verified

`baseline`, `delta`, and `unit` are optional in
`ScenarioParameterChange` (`shadow_trial_contracts.py:77-88`). The engine
validates the target `value` and optional unit, but applies the target value to
the stored sample parameters and never compares the supplied `baseline` to an
authoritative origin/sample value (`shadow_trial_engine.py:101-130`).

The direct golden-ensemble probe supplied `baseline=999.0`,
`value=1.15`, and a self-consistent `delta=-997.85`. It was accepted with two
valid pairs and the normal afterload effect:

```text
declared-baseline-mismatch accepted valid_pairs=2
first_delta={'ejection_fraction_pct': -1.249999999999993}
```

The API therefore records a scenario description that can claim a false
starting point while the computation uses only `value`. Required remediation:
derive the baseline metadata from the selected origin/ensemble, or make the
field semantics explicit and verify it against an authoritative baseline with a
documented tolerance. Do not persist an unverified client claim as provenance.

## Additional hardening note

The effects and pair handlers index raw persisted dictionaries directly
(`api.py:239-246` and `:258-261`). The store verifies only that persisted JSON
is an object, not that it validates as `ShadowTrialResult`. A damaged or
out-of-version record can therefore become a `KeyError`/response-validation
failure rather than a controlled API error. Before exposing these endpoints
outside the demo, validate records on read against versioned response models
and map schema/version failures to the same safe service-error envelope.

## Evidence executed

Focused backend tests run in this review:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q \
  python/hearttwin/tests/test_shadow_trial_api.py \
  python/hearttwin/tests/test_shadow_trial_contracts.py \
  python/hearttwin/tests/test_shadow_trial_store.py
16 passed, 8 warnings in 1.25s
```

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q \
  python/hearttwin/tests/test_shadow_trial_identity.py \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_shadow_trial_golden.py
16 passed in 0.14s
```

The OpenAPI and error-envelope results above came from read-only Python
`TestClient`/`app.openapi()` probes after those tests. No full-suite,
frontend, browser, deployment, or production-host verification was run as
part of this review.

## Gate decision

**M6 API contract/safety gate: FAIL.** The tested success path is usable for a
controlled local demo, but the missing disclaimer on 4xx responses is a
blocking safety contract defect. F-01 should be fixed and regression-tested
before the API is presented as complete; F-02 through F-04 should be resolved
before treating the contract as stable or exposing it to untrusted clients.

## Post-review resolution

This review is a pre-repair snapshot. The lead subsequently added canonical
disclaimer-bearing M6 error envelopes, typed effects/pair response models,
persisted-result revalidation, and synchronized frontend definition/effects
types. Absolute-target semantics and inert scenario text are now documented;
baseline metadata remains explicitly bounded rather than treated as
sample-level truth. The focused Shadow Trial suite now passes 39 tests and the
full Python suite passes 909 tests with 1 skipped.
