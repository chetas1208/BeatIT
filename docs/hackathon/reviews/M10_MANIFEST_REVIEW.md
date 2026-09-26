# M10 Manifest, Architecture, and Provenance Review

## Scope

This review audits `RELEASE_MANIFEST.json` against the repository's package
metadata, backend version constants, frontend execution path, model manifest,
fixtures, architecture description, and executable tests. It is a read-only
release audit; no production or test code was changed.

## Verdict

**PARTIAL — the manifest is parseable and its file references resolve, but it
is not a sufficient or fully accurate release authority.** The declared
`release_status: "not_ready"` is consistent with the open M10 release gates.
The manifest must not be used to claim a shipped M10 release until the version
mismatches and provenance omissions below are corrected or explicitly mapped.

## Manifest field audit

| Field | Repository evidence | Result |
|---|---|---|
| `product` | Repository/package identity is BeatIT (`RELEASE_MANIFEST.json`, `package.json`). | PASS |
| `release_candidate` | `m10-rc-1` exists only in the manifest; no tag, immutable artifact, or manifest test binds it to a source revision. | OPEN |
| `source_identifier` | `working-tree-2026-09-26` records a date but not a commit, tree hash, or clean-tree state. The current worktree contains uncommitted changes. | OPEN |
| `frontend_version` | Matches `package.json` and `web/package.json`, both `0.1.0`. | PASS |
| `api_version` | Matches the FastAPI application version in `python/hearttwin/api.py` (`0.1.0`) and `pyproject.toml`. | PASS |
| `physiology_version` | `canonical-repository-engine` is not an executable version constant. The backend ensemble and Shadow Trial paths use `m5.5-ensemble-projection-v1`; the manifest does not identify a canonical-core source digest. | OPEN |
| `ensemble_version` | `m5.5-ensemble-projection-v1` matches the backend `physiology_version`, but the adjacent contract versions `m5.5-backend-ensemble-v1` and `m5-priors-v1` are omitted. | PARTIAL |
| `shadow_trial_version` | Matches `SHADOW_TRIAL_ENGINE_VERSION` and `TRIAL_ENGINE_VERSION`: `m6-shadow-trial-v1`. | PASS |
| `sensitivity_version` | `m8-tier1-bounded-v1` is not found in the implementation. The engine constant is `m8-missing-piece-tier1-v1`; related contracts also expose `m8-tier1-sensitivity-v1` and `m8-missing-piece-v1`. | FAIL |
| `evidence_map_version` | `m8-reviewed-model-proxy-v1` is not found in source. The implementation declares `m8-evidence-map-v1` and `m8-evidence-taxonomy-v1`. | FAIL |
| `model_manifest` | `models/manifest.json` exists, parses, and has numeric `version: 1`; the referenced model paths are metadata/configuration, not proof of a loaded runtime. | PASS with scope note |
| `demo_fixture_version` | `m10-demo-v1` is written by `scripts/seed-demo.sh` into `data/demo/state.json`; the three hashed fixture paths exist. | PASS |
| `safety_boundary` | Matches the repository's educational, non-diagnostic/non-treatment boundary in substance. It is not the canonical `DISCLAIMER` string and should remain descriptive metadata only. | PASS with scope note |
| `release_status` | `not_ready` agrees with `docs/release/RELEASE_CHECKLIST.md` and the unverified deployment/browser/security/persistence gates. | PASS |

## Architecture consistency

`docs/ARCHITECTURE_FINAL.md` describes the same principal backend flow that is
implemented by the API routes:

- `/api/v1/twin/ensemble` creates and persists the M5.5 ensemble;
- `/api/v1/shadow-trials` runs and retrieves paired M6 results;
- `/api/v1/missing-piece` runs and retrieves the M8 analysis; and
- `/api/health/live`, `/api/health/ready`, and `/api/v1/system-status` expose
  runtime readiness and optional-provider status.

The active frontend route follows the stated authority boundary: `web/lib/twin/
ensemble/backend.ts` constructs only the request and maps the backend response;
`web/lib/twin/scenario/useScenario.tsx` calls `generateBackendEnsemble`.
However, `web/lib/twin/ensemble/runner.ts` still contains a local ensemble
evaluator with older `m4-deterministic-v1` and `m5-ensemble-v1` defaults. It is
not the active generation path found in the current scenario hook, but it is a
real alternate implementation and remains covered by frontend tests. The
architecture document should either label this as a quarantined compatibility
path or remove it before claiming one numerical authority.

The architecture's self-host statement is descriptive rather than a verified
deployment contract. `deploy/beatit` and the nginx example exist, but public
reverse-proxy, TLS, restart, and persistence behavior remain open in the M10
release checklist. The manifest therefore cannot upgrade those statements to
deployment evidence.

## Provenance and version consistency

The backend contracts expose more version information than the release
manifest records:

| Capability | Implemented identifiers | Manifest coverage |
|---|---|---|
| M5.5 ensemble | `m5.5-ensemble-projection-v1`, `m5.5-backend-ensemble-v1`, `m5-priors-v1` | Only first identifier represented |
| M6 Shadow Trial | `m6-shadow-trial-v1`, `m6-effect-metrics-v1`, `m6-shadow-provenance-v1` | Only engine identifier represented |
| M8 Missing Piece | `m8-missing-piece-tier1-v1`, `m8-tier1-sensitivity-v1`, `m8-missing-piece-v1` | Declared identifier is absent |
| M8 evidence | `m8-evidence-map-v1`, `m8-evidence-taxonomy-v1` | Declared identifier is absent |
| Scenario persistence | frontend `SCENARIO_PERSISTENCE_VERSION = 1` | Not represented |

The M6 response contract also carries pairing policy and scenario-definition
hash metadata, but the release manifest has no schema/provenance-contract
version field. A consumer cannot determine from the manifest alone whether a
stored artifact is compatible with the M6 provenance envelope.

The M8 audit should not collapse sensitivity-engine, evidence-map, and
evidence-taxonomy versions into one informal label: they govern different
contracts and must be recorded separately if the manifest is intended to be a
reproducibility authority.

## Fixture and model path verification

The following read-only probe passed:

```text
manifest JSON/path probe: PASS
```

Verified paths:

- `models/manifest.json`
- `fixtures/hearttwin/manual_baseline.json`
- `fixtures/golden/probabilistic/fixed-only.json`
- `fixtures/golden/shadow_trials/synthetic-demo-case.json`
- `docs/ARCHITECTURE_FINAL.md`
- `python/hearttwin/api.py`
- `python/hearttwin/ensemble.py`
- `python/hearttwin/shadow_trial_engine.py`
- `python/hearttwin/missing_piece/engine.py`
- `python/hearttwin/missing_piece/evidence.py`

The seed/reset workflow and reproducibility review establish the `m10-demo-v1`
state and fixture hashes. Those hashes are stored in generated
`data/demo/state.json`, not in `RELEASE_MANIFEST.json`; therefore the release
manifest does not itself pin demo content.

## Test evidence

Focused backend contract and golden tests passed:

```text
120 passed, 8 warnings in 4.43s
```

The run covered ensemble contracts/API/store, Shadow Trial contracts/engine/
goldens/identity/reproducibility/store, and M8 evidence/sensitivity behavior.
The source tree contains no executable test that parses `RELEASE_MANIFEST.json`
or asserts its version fields against implementation constants. The manifest
can consequently drift without turning the test suite red.

## Required disposition

Before a final release claim:

1. Replace the two absent M8 identifiers with the actual constants, or add an
   explicit compatibility mapping that names every governed M8 contract.
2. Add M5.5 distribution/prior and M6 provenance/effect-contract identifiers
   to the manifest, or document why they are intentionally excluded.
3. Bind `source_identifier` to an immutable commit/tree digest and record the
   dirty-tree policy for release candidates.
4. Add a small manifest-consistency test that parses the manifest, resolves
   referenced paths, and checks the authoritative version constants.
5. Mark the local frontend evaluator as compatibility/quarantined or remove
   the alternate numerical path so the architecture claim is unambiguous.

**Release gate: OPEN.** This review does not authorize changing
`release_status` to `ready`.
