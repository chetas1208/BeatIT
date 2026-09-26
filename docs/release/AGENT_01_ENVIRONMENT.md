# M10.5 Agent 01 — Environment Audit

**Scope:** BeatIT environment shape, `env_spec`, validation, and runtime configuration.
**Audit date:** 2026-09-26
**Disposition:** **OPEN — local deterministic mode is validated; production environment governance is not release-ready.**

This audit intentionally records variable names, counts, types, and validation
outcomes only. It does not include environment values, credentials, or
secret-derived URLs.

## Sources inspected

- `.env` and `.env.example` (key names and file metadata only)
- `web/.env.example`
- `python/hearttwin/tools/env_spec.py`
- `python/hearttwin/tools/env_config.py`
- `python/hearttwin/tools/model_config.py`
- `scripts/verify_env.py`
- `docs/runtime/ENVIRONMENT.md`
- `docs/runtime/SELF_HOSTING.md`
- `python/hearttwin/tests/test_env_config.py`
- frontend Next.js configuration and environment consumers

## Inventory and shape

| Surface | Observed shape | Result |
|---|---|---|
| Canonical `ENV_SPEC` | 50 entries; 9 marked secret; 0 marked `required_for_production` | **Gap:** production mode has no mandatory environment contract. |
| Root `.env.example` | 148 unique keys; every canonical `ENV_SPEC` key is present | **Partial:** 98 additional CareGuard, dataset, legacy, and integration keys are outside the canonical spec. |
| Private root `.env` | 154 unique keys; no duplicate keys; file mode `0600`; ignored by Git | **Good handling:** private file is not tracked and is owner-readable only. |
| Private-only keys | 7 keys are present in `.env` but absent from `.env.example` | **Gap:** the private runtime shape has undocumented model-pool/role configuration. |
| `web/.env.example` | 11-key frontend/server subset | **Partial:** it is not a complete contract and must remain separate from server secrets. |
| Public-prefixed secret names | No canonical secret is named with `NEXT_PUBLIC_` | **Pass:** no secret variable is intentionally browser-prefixed in the inspected spec. |

The root example includes a non-blank entry for the secret-classified database
variable. The current example-file heuristic checks names containing `API_KEY`
or `TOKEN`, so it does not flag every secret-classified variable, including this
case. The report intentionally does not reproduce the entry's value.

The extended keys are used by runtime code, especially the CareGuard and
imaging paths, but they are not represented in `ENV_SPEC`. This means the
canonical validator does not type-check, require, or secret-classify most of
that extended surface.

## Safe validation performed

The following checks were run without printing values:

| Check | Result |
|---|---|
| Root example keys compared with `ENV_SPEC` | All 50 canonical names present; 98 documented names outside the core spec. |
| Private `.env` key shape | 154 unique names; 0 duplicate names; 5 secret-classified values non-empty in the local process. Values were not displayed. |
| Example secret heuristic | 0 findings under the existing `scripts/verify_env.py` heuristic. This is not proof that every secret-classified key is blank. |
| `validate_env("local-dev")` | Structural result `ok=True`; 0 errors; 10 optional-configuration warnings. Values were not displayed. |
| `validate_environment()` snapshot shape | Passed; returned the expected non-secret status groups for model, Weave, Redis, VISTA, API, intelligence, app, and warnings. |
| Environment test suite | `.venv/bin/python -m pytest -q python/hearttwin/tests/test_env_config.py` — **77 passed**. |

The project virtual environment was used for the test run because the system
interpreter does not contain all repository dependencies. No external provider,
database, Redis service, or model endpoint was contacted by these checks.

## Runtime behavior

The current runtime configuration is intentionally fallback-oriented:

- Provider-backed language features are optional. Missing provider credentials
  produce deterministic fallback behavior where the feature supports it.
- Weave status is derived from configuration presence and trace mode; the health
  snapshot does not prove remote trace delivery.
- Redis memory status is derived from the enable flag and connection-variable
  presence; it does not prove reachability or persistence.
- VISTA status is derived from its enable flag plus endpoint/key presence; it
  does not perform a health request.
- API bases have defaults, and the frontend uses the public API-base variable.
- Safety mode defaults to strict in the runtime helper.
- Per-agent model names have defaults in `model_config.py`, so model names being
  present does not imply that a provider is configured or reachable.

This is appropriate for deterministic local demo operation, but configuration
presence must not be reported as deployment readiness.

## Validation and secrecy findings

1. **Production requiredness is not enforced.** Every `EnvVarSpec` currently
   has `required_for_production=False`; `vercel-production` therefore cannot
   fail solely because a deployment credential or required service setting is
   absent.
2. **The validator is incomplete for the full repository surface.** The core
   spec covers 50 names while the root example contains 98 additional names.
   Extended CareGuard, imaging, dataset, and legacy variables can be misspelled
   without being caught by `validate_env`.
3. **Validation is shallow.** Only selected booleans and numeric fields have
   validators. URL syntax, endpoint scheme, path existence, range constraints,
   cross-variable requirements, and provider reachability are not validated by
   the canonical spec.
4. **The CLI is not fully value-silent.** `scripts/verify_env.py` interpolates
   the configured project name in one warning and the raw invalid value in
   validator error messages. A release-safe validator should emit only the
   variable name, category, and redacted reason.
5. **Example secret detection is narrow.** The example checker looks for
   `API_KEY` and `TOKEN` names and does not cover all variables marked secret in
   `ENV_SPEC`, including database and connection URL variables.
6. **Documentation has a Redis naming mismatch.** The README references an
   Upstash-specific variable family, while the inspected canonical spec and
   runtime helpers use `REDIS_URL`. The deployment contract must choose one
   supported naming scheme or document an explicit adapter boundary.

## Release decision

**Environment gate: OPEN / FAIL for public or clinical-data deployment.**

The local deterministic fallback path is reproducible and the focused test
suite passes. The environment contract is not yet sufficient to assert that a
production deployment has the required credentials, reachable dependencies,
validated extended settings, or safe diagnostic output.

## Required follow-up before an RC

- Define whether the canonical spec owns the extended CareGuard/imaging
  variables or whether each subsystem gets a separately tested spec.
- Mark genuinely mandatory production settings as required, with deployment
  checks that fail closed while preserving the local fallback mode.
- Extend secret detection to every `secret=True` variable and require blank,
  explicit placeholders in public examples, including database/connection
  variables.
- Make validator output value-free, including mismatch and invalid-input
  messages.
- Reconcile the Redis variable names across README, examples, runtime, and
  deployment configuration.
- Add safe cross-variable checks for enabled integrations, without probing or
  printing credentials.
- Re-run the environment suite and a deployed health/readiness check after
  those changes.

