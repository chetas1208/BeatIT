# M9 Architecture Review

Date: 2026-09-26  
Scope: shared shell ownership, providers, navigation route seam, numerical
authority boundaries, and integration risks. Source audit only; no production
files were changed.

## Verdict

**OPEN.** The shell has a clear visual composition and the five product spaces
have one shared registry, but route identity, artifact rehydration, and
numerical ownership are not closed. The current design is suitable as an
in-memory demo scaffold, not yet as a durable architecture boundary.

## Pass findings

### ARCH-P1 — Shared shell ownership is explicit and appropriately centralized

**Pass, source-bounded.** `AppShell` owns the header, primary navigation, three
column layout, intake rail, observability rail, safety modal, Copilot dock, and
error boundaries ([`AppShell.tsx:3-13`](../../../web/components/layout/AppShell.tsx#L3-L13),
[`AppShell.tsx:188-259`](../../../web/components/layout/AppShell.tsx#L188-L259)).
Domain panels remain separate components and are selected through one
`ProductWorkspace` seam ([`AppShell.tsx:71-136`](../../../web/components/layout/AppShell.tsx#L71-L136)).
This gives the shell one owner for cross-cutting layout and avoids each product
space creating a competing application frame.

### ARCH-P2 — Provider boundaries are small and understandable

**Pass, with scope limits.** The root layout owns the global CopilotKit runtime
provider ([`layout.tsx:34-45`](../../../web/app/layout.tsx#L34-L45)). The shell
owns the cardiac temporal and scenario providers around the product workspace
([`AppShell.tsx:220-245`](../../../web/components/layout/AppShell.tsx#L220-L245)).
The temporal provider exposes selected snapshots and visualization projections,
while the scenario provider owns scenario/ensemble session state
([`context.tsx:98-145`](../../../web/lib/twin/integration/context.tsx#L98-L145),
[`useScenario.tsx:44-180`](../../../web/lib/twin/scenario/useScenario.tsx#L44-L180)).
The separation is legible and consumers fail loudly when used outside their
provider.

## Open findings

### ARCH-O1 — The route seam duplicates the App Router entry without making the route authoritative — P0

`/` and `/[mode]` both render the same client `AppShell`
([`app/page.tsx:1-10`](../../../web/app/page.tsx#L1-L10),
[`app/[mode]/page.tsx:1-9`](../../../web/app/%5Bmode%5D/page.tsx#L1-L9)). The
dynamic page validates `mode` server-side, but `AppShell` independently reads
`window.location.pathname` into local state and changes modes with
`history.pushState` ([`AppShell.tsx:139-159`](../../../web/components/layout/AppShell.tsx#L139-L159),
[`navigation.ts:3-20`](../../../web/lib/product/navigation.ts#L3-L20)). The
server route parameter therefore does not drive the rendered mode after
hydration. A direct load can be valid at the HTTP layer while the client falls
back to a different in-memory mode or loses state on remount.

Required closure: choose one authoritative route seam, pass the validated mode
into the shell, and test direct load plus Back/Forward/remount behavior. Keep
CareGuard routes outside this product-mode parser.

### ARCH-O2 — Navigation carries mode only, not artifact identity — P0

`navigateToMode` writes only `{ beatItMode }` and `/${mode}` to history
([`navigation.ts:16-20`](../../../web/lib/product/navigation.ts#L16-L20)). The
session context contains fields for snapshot, ensemble, scenario, trial, pair,
analysis, and target metric, but those values are assembled from mounted
in-memory providers/stores ([`contracts.ts:5-16`](../../../web/lib/product/contracts.ts#L5-L16),
[`AppShell.tsx:84-95`](../../../web/components/layout/AppShell.tsx#L84-L95)). A
reload or deep link cannot prove which artifact a Compare, Evidence, or Report
surface owns. This is the principal integration risk between navigation and
the otherwise typed product contracts.

Required closure: define an opaque artifact identity/deep-link contract and
rehydrate or fail closed when lineage is missing, stale, mismatched, or
deleted. Do not put raw patient payloads in URLs.

### ARCH-O3 — Compare has a separate in-memory ownership boundary — P1

Temporal/scenario state is provider-backed, while paired comparison state is a
module-level Zustand store ([`store.ts:1-23`](../../../web/lib/twin/comparison/store.ts#L1-L23)).
`ProductWorkspace` reads both to construct one session context, but there is no
persisted or route-level transaction tying the selected snapshot, scenario,
ensemble, trial, and pair together. Closing or replacing one upstream artifact
can therefore leave the comparison store holding a plausible but unrelated
pair. This is an integration seam, not a rendering defect.

Required closure: store the complete immutable lineage key with the pair and
reject/clear it when the selected origin or descendant changes.

### ARCH-O4 — Frontend scenario propagation duplicates numerical authority — P0

`web/lib/twin/scenario/propagation.ts` implements baseline metrics, bounded
parameter relationships, EF, SV, CO, MAP, and RR calculations in the browser
([`propagation.ts:108-160`](../../../web/lib/twin/scenario/propagation.ts#L108-L160),
[`propagation.ts:168-190`](../../../web/lib/twin/scenario/propagation.ts#L168-L190)).
The repository's declared numerical authority is the deterministic Python core
(`cardiac_state.py`, `hemodynamics.py`, and `recovery_sim.py`), including the
tested formulas and PV generation ([`cardiac_state.py:30-96`](../../../python/hearttwin/tools/cardiac_state.py#L30-L96),
[`hemodynamics.py:64-160`](../../../python/hearttwin/tools/hemodynamics.py#L64-L160)).
The frontend source reference to `cardiac_state.py` does not prevent behavior
from drifting: the browser has its own coefficients, fallbacks, clamps, and
rounding.

Required closure: make the browser path an input/editor projection only, or
route scenario computation through the backend and render returned canonical
values. If a client preview remains, label it explicitly and add parity tests
against the Python authority; it must not be promoted to canonical output.

### ARCH-O5 — Visualization projection is bounded but can manufacture derived timing — P1

Comparison projection correctly documents that it does not recompute
physiology, and copies canonical scalar values into a visual template
([`projection.ts:15-45`](../../../web/lib/twin/comparison/projection.ts#L15-L45)).
However, it derives `RR = 60000 / HR` in the browser and writes that value into
the visualization ([`projection.ts:21`](../../../web/lib/twin/comparison/projection.ts#L21),
[`visualization.ts:23-44`](../../../web/lib/twin/comparison/visualization.ts#L23-L44)).
That is acceptable only as a declared display projection; it becomes a
numerical-boundary violation if consumers treat the projected visualization as
the canonical cardiac state.

Required closure: preserve the distinction in types and provenance between
backend state, display-only projection, and held PV shape. Do not use projected
values as inputs to another simulation.

## Integration risk summary

| Risk | Current boundary | Consequence | Priority |
| --- | --- | --- | --- |
| Route/client divergence | Next `[mode]` plus local `history.pushState` | Direct links and remounts can disagree with the displayed mode | P0 |
| Artifact loss | Mode-only URL and in-memory providers/stores | Compare/Evidence/Report cannot rehydrate or validate lineage | P0 |
| Numerical drift | Browser scenario formulas plus Python core | Same inputs can produce different canonical-looking outputs | P0 |
| Store mismatch | Provider state combined with comparison Zustand state | A pair can outlive its origin context | P1 |
| Projection promotion | Derived RR and held PV shape in view models | Display-only values may be mistaken for simulated state | P1 |
| Global runtime coupling | CopilotKit provider wraps the whole app | Copilot runtime failure or version changes affect every route | P1 |

## Review boundary

No production edits were made. This document does not claim browser, build,
performance, or end-to-end sign-off; those require a runnable environment and
the route/artifact/numerical contracts above to be closed.
