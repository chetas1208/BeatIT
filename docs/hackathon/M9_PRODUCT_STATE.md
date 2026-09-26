# M9 Product State Contract

Last updated: 2026-09-26

## Purpose and boundary

This document defines the shared product-context contract for the five M9
spaces:

```text
TWIN → EXPERIMENT → COMPARE → EVIDENCE → REPORT
```

The contract governs identity, lineage, navigation, reload, privacy, and
asynchronous result ownership. It does not replace the numerical contracts for
the cardiac model, ensemble generation, Shadow Trial pairing, or Missing Piece
analysis. Those systems remain the authorities for their own payloads. The
frontend may select, display, and invalidate their results; it must not
recalculate or repair them.

Product context is a set of references, not a serialized copy of case data.
The URL, browser storage, and React state must never be treated as an
alternative source of truth for clinical or physiological values.

## Typed context model

The implementation should expose the following semantic types in the product
contract. The brand types are compile-time distinctions over opaque strings;
they do not authorize a caller to manufacture an ID or bypass backend
validation.

```ts
type OpaqueId<Kind extends string> = string & {
  readonly __brand: `BeatIT.${Kind}Id`;
};

type CaseId = OpaqueId<"Case">;
type SnapshotId = OpaqueId<"Snapshot">;
type EnsembleId = OpaqueId<"Ensemble">;
type ScenarioId = OpaqueId<"Scenario">;
type TrialId = OpaqueId<"ShadowTrial">;
type AnalysisId = OpaqueId<"MissingPieceAnalysis">;

type ProductMode =
  | "TWIN"
  | "EXPERIMENT"
  | "COMPARE"
  | "EVIDENCE"
  | "REPORT";

interface ProductContext {
  readonly schemaVersion: "m9";
  readonly mode: ProductMode;
  readonly caseId: CaseId | null;
  readonly originSnapshotId: SnapshotId | null;
  readonly ensembleId: EnsembleId | null;
  readonly scenarioId: ScenarioId | null;
  readonly trialId: TrialId | null;
  readonly analysisId: AnalysisId | null;
}
```

`mode` is a view selection. The IDs are the semantic context. A mode change
does not change the context key and must not invalidate a valid result merely
because the user moved between spaces.

The product state wraps authority-owned payloads in an explicit load state.
Every async result type used by the five spaces must be equivalent to this
shape:

```ts
type LoadState<T> =
  | { readonly status: "empty" }
  | {
      readonly status: "loading";
      readonly requestId: string;
      readonly contextKey: string;
      readonly startedAt: string;
    }
  | {
      readonly status: "ready";
      readonly value: T;
      readonly requestId: string;
      readonly contextKey: string;
      readonly receivedAt: string;
    }
  | {
      readonly status: "stale";
      readonly value: T;
      readonly resultContextKey: string;
      readonly currentContextKey: string;
      readonly reason: StaleReason;
    }
  | {
      readonly status: "error";
      readonly requestId: string;
      readonly contextKey: string;
      readonly message: string;
      readonly retryable: boolean;
    };

type StaleReason =
  | "case_changed"
  | "origin_changed"
  | "ensemble_changed"
  | "scenario_changed"
  | "analysis_changed"
  | "server_revision_changed"
  | "superseded_request"
  | "unknown";
```

The primary surface must render `stale` differently from `ready`. A stale
payload may be retained briefly for a visible transition or an explicit
inspection disclosure, but it must not supply values to a child request, a
report, an accessibility announcement that says the result is current, or a
new calculation. Clearing the value to `empty` is preferred when an ancestor
changed or when the retained payload could be mistaken for the new context.

### Context key

`contextKey` is a deterministic serialization or digest of the semantic
references and the input revision that produced a result. It must include the
following when present, in a stable order:

```text
schemaVersion
caseId
originSnapshotId
ensembleId
scenarioId
trialId
analysisId
```

For computation results, the key must also include the authority-provided
fingerprint or version of the input definition. Examples are the Shadow Trial
`fingerprint`, the exact ensemble identity and configuration, and the Missing
Piece target/evidence request. `mode`, selected card, camera state, and other
presentation-only values are not part of the computation key.

The key is an internal freshness guard. It is not a secret, is not a substitute
for authorization, and must not be used as a URL parameter when it contains
more information than an opaque persisted ID.

## Lineage and valid combinations

References form a dependency chain. A child is valid only when the backend
confirms that it belongs to the current parent and that its stored lineage is
consistent.

```text
case
 └─ origin snapshot
     ├─ baseline ensemble
     │   ├─ scenario definition
     │   │   └─ Shadow Trial
     │   └─ Missing Piece analysis
     └─ report projection (references the selected valid descendants)
```

Required equality/compatibility checks are:

- `originSnapshotId` belongs to `caseId`.
- `ensembleId` was generated from `originSnapshotId` and the current
  authority versions/configuration.
- `scenarioId` has the same origin snapshot as the ensemble. A scenario is an
  immutable definition; editing controls creates a new definition identity or
  a new input revision.
- `trialId` names a persisted Shadow Trial whose baseline ensemble and
  scenario match the current `ensembleId` and `scenarioId`. Its paired result
  remains the backend authority; the browser does not re-pair samples.
- `analysisId` names a persisted Missing Piece result whose baseline ensemble,
  target metric, and declared evidence request match the current context.
- A report is a deterministic projection of the valid references above. It is
  not a second numerical authority and does not receive a permanent
  `reportId` unless a future backend contract explicitly adds one.

The absence of a child ID is meaningful. It means that the user has not yet
selected or produced that artifact; it does not mean that an empty result,
zero effect, or unavailable measurement was computed.

### Space requirements

| Space | Minimum context | Ready result requires | Permitted incomplete state |
|---|---|---|---|
| `TWIN` | `caseId` | case and selected origin/snapshot data | no case, or case loading/error |
| `EXPERIMENT` | `caseId`, `originSnapshotId` | matching ensemble and immutable scenario definition | draft scenario, no ensemble, or loading |
| `COMPARE` | `caseId`, `ensembleId`, `scenarioId` | matching completed `trialId` | setup, loading, failed, or no valid pairs |
| `EVIDENCE` | `caseId`, `ensembleId` | matching `analysisId` and target/evidence request | no analysis, loading, unavailable evidence, or incomplete coverage |
| `REPORT` | `caseId` | all referenced inputs are `ready` for the report revision | report unavailable, partial, or stale |

`COMPARE` must not show a previous trial as the current comparison while a new
trial is loading. `EVIDENCE` must not infer that missing evidence has zero
impact. `REPORT` must identify omitted, unavailable, stale, and synthetic
inputs rather than filling gaps with values from another revision.

## Preservation and invalidation rules

State transitions are dependency ordered. Preserve an ancestor only when its
identity and authority revision remain unchanged. Invalidate descendants as a
unit when their required parent changes.

| Event | Preserve | Invalidate or reset |
|---|---|---|
| Switch between the five spaces | all valid context and payloads | none; only `mode` changes |
| Change tab, drawer, camera, metric presentation, or selected valid pair | all computation payloads | presentation selection only; if the pair is no longer present, select the first valid pair deterministically |
| Create or select a different case | none of the old case's active results | case descendants, in-flight requests, active scenario, trial, analysis, and report |
| Add/extract/operate new source data that produces a new snapshot | case identity and source history | selected origin and every ensemble, scenario result, trial, analysis, and report derived from the old snapshot |
| Select a different origin snapshot in the same case | case and the newly selected snapshot | ensemble and every descendant of the old origin |
| Change ensemble seed, sample count, distributions, priors, or physiology version | case and origin | ensemble result and all scenario, trial, analysis, and report descendants |
| Edit, reset, undo, or redo a scenario definition | case, origin, and an ensemble only if its exact input key remains valid | the active scenario computation, trial, analysis, and report; clear the ensemble association when the current implementation couples it to the scenario revision |
| Submit a new Shadow Trial | case, origin, ensemble, and scenario | the previous trial is no longer current; mark it stale or remove it from the primary comparison until the new request completes |
| Change Missing Piece target metric or evidence request | case, origin, ensemble, and unrelated trial | current analysis and report; never reuse a result for another target/request |
| Generate or refresh a report | all valid source results | only the previous report projection; source results remain valid |
| Server reports deletion, 404, incompatible lineage, or revision mismatch | nearest verified ancestor | the missing object and every descendant; show a recoverable unavailable/stale state |
| Browser back/forward to a different context | references verified for the destination | destination descendants that fail lineage checks; do not retain the prior page's payload under the new URL |

Invalidation is immediate from the user's perspective. A prior response may be
retained in an internal cache only under its complete context key and may be
shown again only after the key is revalidated. A generic “last result” cache is
not allowed.

## Deep-link contract and privacy

Deep links are navigation hints for persisted artifacts, not data exports. The
canonical semantic form is:

```text
/<mode>?case=<opaque-case-id>&snapshot=<opaque-snapshot-id>&ensemble=<opaque-ensemble-id>&scenario=<opaque-scenario-id>&trial=<opaque-trial-id>&analysis=<opaque-analysis-id>
```

The route implementation may use equivalent path segments, but it must keep
the same allowlisted fields and dependency meaning. It must canonicalize the
URL by removing unknown, duplicate, malformed, or descendant-without-parent
parameters. Draft scenario values do not belong in a deep link; only a
persisted immutable scenario ID may be linked.

The following rules are mandatory:

- IDs in URLs must be opaque, non-semantic, bounded in length, and safe to
  display in browser history, server access logs, analytics, screenshots, and
  referrer metadata. If an existing backend ID can encode a name, email,
  patient identifier, filename, or clinical value, it must not be used as a
  public deep-link token.
- URLs must contain no patient notes, uploaded content, filenames, raw
  evidence, physiological measurements, model outputs, prompts, safety
  tokens, API keys, cookies, or bearer credentials.
- A URL must not grant access. The backend remains responsible for existence,
  authorization, case ownership, and lineage checks on every fetch. A copied
  link to an unavailable or unauthorized artifact must resolve to a safe
  unavailable state, not reveal whether another user's artifact exists.
- The default public/demo deployment may use deep links only for synthetic or
  explicitly shareable records. It must not imply that a URL is a private
  clinical record link.
- The application should send `Referrer-Policy: no-referrer` (or the strictest
  deployment-equivalent policy) and must not forward product URLs to external
  telemetry as raw context. If analytics are enabled, IDs must be redacted or
  irreversibly hashed before collection.
- Browser storage may remember non-sensitive presentation preferences such as
  reduced motion or disclaimer acknowledgement. It must not be the durable
  source for case payloads, uploaded content, physiological results, tokens,
  or a hidden copy of a stale trial/analysis.
- “Copy link” is available only after the referenced IDs are persisted and
  lineage-validated. Copying a link never serializes the current draft or
  unsaved numeric controls.

Deep-link parsing is untrusted input. Validate the mode and each ID before
constructing an API path, encode IDs at the request boundary, and reject
oversized or control-character-containing values. Do not use URL text as a
display label without escaping it.

## Reload and rehydration rules

Reload starts a new in-memory session. It does not restore loading promises,
component-local response objects, or a previous result merely because the
browser happened to retain them.

On boot or direct navigation:

1. Parse the allowlisted route and create a context containing only validated
   opaque references. If the URL has no case, start at an empty `TWIN` state.
2. Load the case first. Until it succeeds, do not request or render any
   descendant payload.
3. Resolve descendants in dependency order: origin/snapshot, ensemble,
   scenario, trial, and analysis. Each response must be checked against the
   expected parent IDs and authority fingerprint before it becomes `ready`.
4. If a child is missing, unauthorized, malformed, or lineage-incompatible,
   drop that child and all of its descendants from the active context. Keep
   the nearest verified ancestor and show a recoverable message explaining
   which artifact could not be restored.
5. If the requested mode requires the dropped child, keep the mode when it
   can show an honest setup/unavailable state; otherwise route to the nearest
   valid space without pretending that the requested result exists.
6. Never automatically rerun a simulation, ensemble, Shadow Trial, or Missing
   Piece analysis during reload. A user action may explicitly run it again.
7. Never reconstruct a persisted result from URL parameters, local storage, a
   prior React snapshot, or a partial response. Use the backend GET contract
   for persisted artifacts.
8. When reload completes, the safety disclaimer and the artifact's provenance
   and synthetic/observed/derived labels must be restored with the result.

Reload must be idempotent: revisiting the same validated deep link produces the
same context key and the same authority-owned artifact, subject only to a
server-declared unavailable or version-mismatch response. A network failure is
an error or retry state, never permission to display an old unrelated result.

## Async and stale-result rules

Every request captures both a fresh `requestId` and the complete `contextKey`
at dispatch time. A response may commit only when all of these conditions hold:

```text
requestId is still current for that resource
AND response context key equals current context key
AND response parent IDs equal current parent IDs
AND response is valid for the requested operation
```

If any condition fails:

- ignore the response for visible state;
- do not replace a newer error, loading state, or result;
- do not show a success toast or announce completion;
- do not append the response to a report or pass it to another operation; and
- cancel the request when practical, while retaining the commit guard because
  cancellation is not guaranteed.

When a context mutation occurs, increment the resource revision or otherwise
make all prior request IDs non-current before starting the next request. An
error from an obsolete request is stale too and must not overwrite the current
state.

The UI rules are:

- `loading` means the current context has an active request; it must not show
  old values as if they belong to the request.
- `ready` means the payload was fetched for the exact current key. It does not
  mean that the payload is clinically true; provenance and the canonical safety
  disclaimer remain visible according to the surface contract.
- `stale` means “previously valid for another context.” It must be visibly
  labelled and must offer discard or rerun. It is never equivalent to
  `ready`.
- `error` preserves the current context key and the backend's safe error
  information. It must not silently fall back to a previous result.
- An empty distribution, invalid pair set, unavailable metric, or incomplete
  evidence response is a valid authority response with its declared limitation;
  it is not a stale-result condition and must not be converted into zeroes.

For a result that arrives after a scenario edit, new case, changed target, or
new trial submission, the correct behavior is no visible commit. The old
result may remain on the server as a historical persisted artifact, but it is
not the active product result until the user navigates to and revalidates its
exact context.

## Acceptance checks

M9 product-state work is complete only when the implementation can demonstrate
the following without relying on browser luck or hidden mock data:

- switching among all five spaces preserves a valid case and valid descendant
  results;
- changing an ancestor clears or marks every dependent result stale, with no
  stale value presented as current;
- a late response from an older case, scenario, trial, or analysis cannot
  overwrite the current screen;
- a direct deep link contains only allowlisted opaque IDs and cannot expose
  case content or credentials;
- reload restores persisted artifacts only after dependency and lineage
  validation, and does not silently rerun or reconstruct a result;
- missing, unauthorized, incompatible, and unavailable descendants fall back
  to the nearest honest ancestor/state; and
- report output is generated only from current, ready, authority-owned inputs
  and clearly carries the safety and provenance boundary.

