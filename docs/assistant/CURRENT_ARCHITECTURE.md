# Current Architecture Audit — for Wave 2 (Unified Conversation Architect)

Audit date: 2026-09-26. Scope: pure discovery, no code changes.

## Summary

The frontend migration to Next.js + CopilotKit that `AGENTS.md`/`docs/TASKS.md`/`docs/PLANNING.md`
describe as **future work** is already **done and shipped**. On top of that,
a second, independent product surface ("CareGuard", built at a later, different
hackathon) added its **own bespoke chat widget backed by Anthropic directly**,
bypassing CopilotKit entirely. The repo today therefore has **two live,
architecturally unrelated assistants**:

1. **"Cardiology Copilot"** — real CopilotKit AG-UI wiring: Next.js route →
   `CopilotRuntime` → Python `add_fastapi_endpoint` → OpenAI-only actions,
   with generative-UI cards and one human-in-the-loop step. This is the
   assistant `AGENTS.md` describes.
2. **"CareGuard analysis copilot"** — a hand-rolled floating chat panel that
   calls a plain REST endpoint (`POST /api/v1/careguard/cases/{id}/copilot`)
   backed by a separate Anthropic Claude client/agent stack
   (`python/hearttwin/careguard/anthropic/`). It has no CopilotKit
   involvement: no shared runtime, no shared message history, no generative
   UI, no readable context.

The two are currently kept from colliding only by a UI-level hack: `AppShell.tsx`
hides the CopilotKit dock's launcher button when the CareGuard tab is active
(`web/components/layout/AppShell.tsx:186-191`), because "CareGuard tab has its
own dedicated analysis copilot ... so the cardiac-twin CopilotDock is
suppressed there to avoid two launchers" (comment, same lines). This is exactly
the fragmentation a unification effort needs to resolve — the constraint isn't
"build CopilotKit," it's "fold an existing, working, differently-architected
Anthropic-backed assistant into the existing, working CopilotKit assistant."

**`AGENTS.md`, `docs/TASKS.md`, and `docs/PLANNING.md` are stale** relative to
the repo's actual state — they describe an earlier hackathon ("WeaveHacks 4",
Nuxt/Vue frontend, Upstash REST Redis, HF Spaces deploy) that has since been
superseded by a full Next.js/CopilotKit rebuild and a second "Abridge
Hackathon" CareGuard module, per `README.md:154-193`. Every discrepancy is
flagged inline below.

---

## Frontend Stack State

**Next.js App Router migration: complete, not in progress.** `web/app/` uses
pure App Router conventions (`web/app/layout.tsx`, `web/app/page.tsx`,
`web/app/careguard/{page.tsx,cases/page.tsx,runner/page.tsx}`,
`web/app/api/copilotkit/route.ts`). There is no `web/pages/` directory and no
`nuxt*` file anywhere in the repo (`find . -iname "nuxt*"` → empty). The
legacy `app/composables/useDualBeatApi.ts` that `AGENTS.md` and this task's
brief point to **no longer exists** — it was fully ported/replaced by
`web/lib/api.ts`.

Key dependencies, from `web/package.json:12-31`:
- `next`: `16.2.7` (App Router, Node runtime)
- `react` / `react-dom`: `19.2.4`
- `@copilotkit/react-core`, `@copilotkit/react-ui`, `@copilotkit/runtime`,
  `@copilotkit/runtime-client-gql`: all pinned to `1.59.5`
- `@anthropic-ai/sdk`: `^0.112.3` (present in the **frontend** `package.json`,
  currently unused by any file found in this audit — worth checking in Wave 2
  whether it's dead weight or a planned client-side Anthropic path)
- `openai`: `6.42.0` (used server-side only, in the CopilotKit route)
- `zustand`: `5.0.3` (the single client state store, `web/lib/store.ts`)
- `three` / `@react-three/fiber` / `@react-three/drei`, `plotly.js-dist-min`,
  `motion` — 3D twin + charts + animation, unrelated to the assistant work.

`web/AGENTS.md:1-5` carries a Next.js-specific warning worth respecting
verbatim: *"This version has breaking changes ... Read the relevant guide in
`node_modules/next/dist/docs/` before writing any code."* Next 16 App Router
APIs may differ from training-data assumptions.

## CopilotKit Wiring State

Fully wired end-to-end, not a stub:

- **Node route**: `web/app/api/copilotkit/route.ts` — `export const runtime =
  "nodejs"` (line 10, correctly not `"edge"`) and `export const dynamic =
  "force-dynamic"` (line 13). Builds a `CopilotRuntime` with
  `remoteEndpoints: [copilotKitEndpoint({ url: `${apiBase}/copilotkit` })]`
  (lines 39-41), where `apiBase` resolves from `API_BASE` →
  `NEXT_PUBLIC_API_BASE` → `http://localhost:8000` (lines 34-37). Service
  adapter is `OpenAIAdapter` when a model is configured, else `EmptyAdapter`
  (lines 65-75) — the Node route itself never talks to a model except as the
  AG-UI transport; all four exported handlers (`GET`/`POST`/`OPTIONS`) share
  one cached handler (lines 47-99).
- **Backend AG-UI endpoint**: `python/hearttwin/api.py:122` —
  `add_fastapi_endpoint(app, _copilot_sdk, "/copilotkit")`, imported from
  `copilotkit.integrations.fastapi` (`python/hearttwin/api.py:35`). CORS is
  wide open: `allow_origins=["*"]` (`python/hearttwin/api.py:96-97`).
- **Actions**: `python/hearttwin/copilot.py` defines five CopilotKit
  `Action`s via `build_actions()` (lines 538-651) assembled into a
  `CopilotKitRemoteEndpoint` by `build_sdk()` (lines 654-656): `create_case`,
  `extract`, `operate`, `simulate_recovery`, and `answer_case_question` (the
  **only** LLM-backed action — every other action is a thin, deterministic
  wrapper around the existing pipeline, per the module's own design-rules
  docstring at lines 7-17). Safety is enforced both on input
  (`check_request_safety`) and output (`_check_output_safety`,
  lines 418-448) for every LLM answer.
- **Client provider**: `web/components/copilot/CopilotProvider.tsx` mounts
  `<CopilotKit runtimeUrl="/api/copilotkit">` at the app root
  (`web/app/layout.tsx:4,42`) and themes it via CSS custom properties
  (lines 29-37).
- **Client chat surface**: `web/components/copilot/CopilotDock.tsx` — a
  floating dock using `CopilotChat` (line 599), `useCopilotReadable` to
  expose live case state (lines 361-367), `useCopilotAction` with
  `available: "disabled"` + custom `render` for **generative UI** cards
  mirroring each backend action (`create_case`, `extract`, `operate`,
  `simulate_recovery`; lines 373-533), and one
  `renderAndWaitForResponse` **human-in-the-loop** action,
  `confirm_recovery_simulation` (lines 536-556), rendered by
  `RecoveryConfirmCard` (lines 690-783) which calls the injected `respond()`
  callback. This already satisfies AGENTS.md §5's CopilotKit "Definition of
  Done" bar (drives the pipeline, ≥1 gen-UI component, ≥1 HITL step).
- **Not present**: `useCoAgent` shared-state mirroring (listed as task
  `TC.6`/`[W]` in `docs/TASKS.md`, cuttable) — no occurrences found in the
  frontend.

**Discrepancy vs. this task's brief and `AGENTS.md`**: both frame CopilotKit
wiring as something to check "if any." It is not partial — it is a complete,
working implementation with generative UI and HITL already exceeding the
hackathon Definition-of-Done bar in `AGENTS.md` §5.

## Existing API Contract

`web/lib/api.ts` (287 lines) is a typed fetch client for `NEXT_PUBLIC_API_BASE`
(`/api/v1`), throwing `ApiRequestError` on any failure (no silent fallback —
documented in the file's own header comment, lines 1-12). Methods and the
backend routes they call:

| Client fn (`web/lib/api.ts`) | Backend route |
|---|---|
| `createCase` (138-145) | `POST /cases` |
| `getCase` (147-149) | `GET /cases/{id}` |
| `uploadFile` (151-161) | `POST /cases/{id}/files` |
| `extract` (163-171) | `POST /cases/{id}/extract` |
| `operate` (173-181) | `POST /cases/{id}/operate` |
| `simulateRecovery` (183-191) | `POST /cases/{id}/simulate-recovery` |
| `selfImprove` (193-198) | `POST /cases/{id}/self-improve` |
| `createTwinEnsemble` (200-205) | `POST /twin/ensemble` |
| `getTwinEnsemble` (207-209) | `GET /twin/ensemble/{id}` |
| `getTrace` (215-219) | `GET /cases/{id}/trace` |
| `traceStreamUrl` (225-232) | `GET /cases/{id}/trace/stream` (SSE, URL builder only) |
| `systemCheck` (238-240) | `GET /system-check` |
| `redisStats` (259-269) | derived from `systemCheck` (no dedicated Redis REST route exists — documented deliberately in the file, lines 242-250) |

This client is CopilotKit-independent: CopilotKit's actions in
`python/hearttwin/copilot.py` call the same underlying pipeline functions
(`run_extraction_pipeline`, `run_operation_pipeline`, `run_recovery_pipeline`
from `python/hearttwin/orchestrator.py`) directly rather than going through
this REST client, so the two paths (chat-driven vs. form-driven) can diverge
in behavior if not kept in sync manually — worth a note for Wave 2 if it
plans to route more UI actions through the copilot.

**Second, parallel API client for CareGuard**: `web/lib/careguardApi.ts` has
its own `copilot` method (lines 120-123) hitting
`POST /cases/{caseId}/copilot` under the CareGuard router prefix (full path
`/api/v1/careguard/cases/{case_id}/copilot`), wired in
`python/hearttwin/careguard/routes_analysis.py:50-54`, which calls
`copilot_answer` from `python/hearttwin/careguard/copilot_agent.py`. That
agent module (`used_anthropic: bool = False` field at line 32, set `True` at
line 125 on a live Anthropic call, deterministic fallback returned at line
164) uses Anthropic Claude directly — not OpenAI, not CopilotKit's runtime,
not `python/hearttwin/copilot.py`.

## Conversation/Context Persistence State

**None exists today, for either assistant.** A repo-wide grep for
`conversationId`, `sessionId`, `chatHistory`, `conversation_id`, `session_id`
across `web/`, `python/`, and `api/` (excluding `node_modules`/`.next`)
returned zero matches. Concretely:

- CopilotKit's `CopilotDock` keeps chat turns only in the CopilotKit React
  runtime's own in-memory state (no `useCoAgent`, no localStorage read/write,
  no server-side session store observed).
- CareGuard's `CareGuardCopilot.tsx` keeps its `turns: Turn[]` in a plain
  `useState` (`web/components/careguard/CareGuardCopilot.tsx:18`) — lost on
  unmount/refresh, never persisted.
- The backend has **no** conversation/session table. `CaseRecord` (the only
  durable case-scoped state, persisted via `python/hearttwin/tools/storage.py`
  and optionally Redis) has no message-history field in either the
  CopilotKit action payloads or the CareGuard copilot agent.

Any conversation memory / cross-turn context Wave 2 wants must be built from
scratch; there is no existing store or schema to migrate.

## Artifact/Generative-UI Precedent

Yes — a real, reusable pattern exists in `CopilotDock.tsx`:
- `GenCard` (lines 128-179): a themed card shell with an icon, eyebrow label,
  title, and a `status` chip that switches "Running" ⇄ "Done", driven by
  CopilotKit's own `inProgress`/`executing`/`complete` action status.
- `GenFailCard` (182-200): an honest failure card (no fake success) shown
  when a backend action result carries `status: "failed"`.
- `Stat` (203-234): one labelled numeric tile, reused across the `operate`
  card's four metrics.
- `RunningRows` (237-251): a streaming shimmer placeholder while an action is
  in flight.
- `RecoveryConfirmCard` (690-783): the HITL confirm/decline card pattern
  (calls the CopilotKit-provided `respond()` callback).

CareGuard's UI has **no equivalent typed card system** — `CareGuardCopilot.tsx`
renders answers as plain inline-styled `div`s (`qBubble`/`aBubble`, lines
97-104), and other CareGuard views (`web/components/careguard/**`) use their
own report/evidence-table components independent of the `GenCard` family.
If Wave 2 wants one generative-UI vocabulary across both assistants, `GenCard`
in `CopilotDock.tsx` is the existing precedent to extend or extract, not
something to invent fresh.

## Streaming State

- **SSE is real and load-bearing**, but only for the agent trace, not for
  chat: `useTraceStream` (`web/hooks/useTraceStream.ts`) opens a browser
  `EventSource` against `traceStreamUrl()` (`web/lib/api.ts:225-232`), with
  `Last-Event-ID`-based resume (`web/hooks/useTraceStream.ts:56-64`) and named
  event listeners for `stream_setup`, `agent_stage`, `tool_call`,
  `redis_error`, `trace` (lines 102-111). This matches AGENTS.md §4's Redis
  guidance (`XADD`/`XRANGE`-by-last-id → SSE → `EventSource`), though see the
  Redis section below for a stack change.
- **CopilotKit chat streaming**: handled entirely inside
  `@copilotkit/runtime`/`@copilotkit/react-core` (standard library behavior,
  not custom code in this repo) via the Node route's `handleRequest`.
- **CareGuard chat**: `careguardApi.copilot()` is a single non-streaming
  `fetch`/JSON round trip (`web/lib/careguardApi.ts:120-123`) — no streaming
  at all, the whole answer arrives at once.

## Deploy Constraints Relevant To New Assistant Backend

**Major discrepancy from `AGENTS.md` §4 "Deploy (WS-E)":** AGENTS.md mandates
backend on **Hugging Face Spaces (Docker)**, explicitly forbidding Vercel
Python functions. The actual repo does the opposite:

- `vercel.json:5-16` routes `/api/:path*` → `api/index.py` as a **Vercel
  Python serverless function** with `"maxDuration": 60, "memory": 1024`.
- `api/index.py` (3 lines) simply re-exports `python.hearttwin.api:app`.
- `README.md:144-146`: *"the backend as a Python serverless function from the
  repo root (`vercel.json` routes `/api/:path*` → `api/index.py`)"*.
- There is **no `Dockerfile`** anywhere in the repo (`find . -iname
  "*dockerfile*"` → empty) and **no mention of Hugging Face/HF Spaces**
  anywhere in the codebase (`grep -rl "huggingface\|Hugging Face\|Spaces"` →
  empty). `deploy/README.md` (the only file in `deploy/`) instead describes a
  generic self-hosted deployment (Next.js + FastAPI + Postgres + Redis +
  reverse proxy), not HF Spaces.

**Consequence for any new/expanded assistant backend route**: it will very
likely run as a **Vercel Python serverless function with a 60-second
`maxDuration`** (per `vercel.json:12-15`), not on an always-on Docker host.
This matters a great deal for a unified assistant:
- Long-running or slow-to-flush operations (multi-step tool chains, Weave
  trace flush, an Anthropic call with retries) must fit inside that 60s
  budget or degrade gracefully.
- No confirmed WebSocket support in a Vercel Python function — the existing
  SSE trace stream already routes around this by using SSE, not WebSockets;
  a new assistant streaming path should follow the same pattern rather than
  assume a persistent socket.
- Frontend stays on Vercel (Next.js, Root Directory `web`, per README) with
  its own separate serverless/Node functions (the CopilotKit route is
  explicitly pinned to the Node runtime, not edge — `route.ts:10`).
- If Wave 2's plan assumes AGENTS.md's HF-Spaces-Docker backend (persistent
  process, no SIGTERM-on-timeout risk), **that assumption is currently false
  for this repo** and should be re-verified with a human before being relied
  upon, since it changes what's safe to build (e.g., whether a long-lived
  in-process conversation cache is viable at all across serverless
  invocations).

## Weave/Tracing Current State

`AGENTS.md` §4's claim that `_publish()` "calls a non-existent
`client.publish()`" is **still accurate today** —
`python/hearttwin/tools/weave_trace.py:174-175`:
```python
if hasattr(_WEAVE_CLIENT, "publish"):
    _WEAVE_CLIENT.publish(payload)
```
This is guarded by `hasattr` (so it won't hard-crash), but `weave.Client`
objects returned by `weave.init()` do not expose a `.publish()` method in
current Weave versions, so this remains a **best-effort no-op** in practice;
the actual durable trace record is the local in-process dict
(`_LOCAL_TRACES`/`_LOCAL_RUNS`, lines 14-16). `weave.init(project)` **is**
called (line 283, inside `_init_weave()`), but:
- There is **no `@weave.op` decoration** anywhere in `python/` — a repo-wide
  grep for `weave.op`/`@weave` found only a docstring reference in
  `python/hearttwin/copilot.py:16` ("OpenAI calls are autopatched by Weave"),
  not an actual decorator on any orchestrator/agent function. So nested
  pipeline→agent→tool call trees, as AGENTS.md §4 requires, are **not**
  produced by real Weave instrumentation — only by the hand-rolled
  `TraceSink`/`TraceContext` classes in this file, which build their own
  JSON tree independent of Weave.
- No `client.flush()` or equivalent call was found anywhere in `python/`.
- No `weave.get_current_call().ui_url` usage was found; `get_run_url()`
  (lines 260-264) instead **constructs** a URL string
  (`f"{project_url}/runs/{run_id}"`) rather than reading a real per-call URL
  from the Weave SDK, so it is not guaranteed to resolve to an actual trace.

Net: Weave is initialized but not truly instrumented — AGENTS.md's framing of
this as "a real build task, not polish" remains correct and unresolved. Any
Wave 2 work that assumes traces already nest per-agent in the public Weave UI
should not rely on that being true yet.

## Architecture Constraints For Wave 2

- **Two assistants exist today and both work** — CopilotKit's "Cardiology
  Copilot" (`web/components/copilot/CopilotDock.tsx` +
  `python/hearttwin/copilot.py`) and CareGuard's bespoke Anthropic-backed
  "analysis copilot" (`web/components/careguard/CareGuardCopilot.tsx` +
  `python/hearttwin/careguard/copilot_agent.py`). Unification means merging
  or bridging these two, not building a first CopilotKit integration from
  scratch.
- **Do not regress the existing CopilotKit gen-UI/HITL implementation** —
  `create_case`/`extract`/`operate`/`simulate_recovery` generative cards and
  the `confirm_recovery_simulation` human-in-the-loop step in
  `CopilotDock.tsx` already meet AGENTS.md §5's CopilotKit Definition of
  Done; any redesign should extend `GenCard`/`RecoveryConfirmCard`-style
  patterns rather than replace working UI wholesale.
- **CareGuard's Anthropic path is a distinct provider and safety pipeline**
  (`python/hearttwin/careguard/anthropic/` — model router, refusal handling,
  redaction, structured output) that is not routed through OpenAI or
  CopilotKit's `OpenAIAdapter`/`EmptyAdapter`. A unified assistant must decide
  whether CareGuard questions get proxied through CopilotKit's
  `remoteEndpoints`/actions (adding an `answer_careguard_question`-style
  action to `python/hearttwin/copilot.py`) or whether CopilotKit's runtime
  needs a second, Anthropic-backed service adapter path — this is a decision
  point, not settled.
- **No conversation/session persistence exists anywhere** (frontend or
  backend) for either assistant — building one is greenfield work with no
  legacy schema to respect, but also nothing to migrate away from.
- **Must not assume Hugging Face Spaces / Docker deployment** — the backend
  today deploys as a **Vercel Python serverless function**
  (`vercel.json:5-16`, `api/index.py`) with a **60-second `maxDuration`** and
  1024MB memory. AGENTS.md's HF-Spaces guidance is stale; a new assistant
  backend route must work within Vercel serverless constraints (short
  timeout, no guaranteed persistent process, no confirmed WebSocket support)
  unless a human explicitly re-platforms the backend.
- **The CopilotKit Node route must stay on the Node runtime, not edge** —
  already correctly set (`web/app/api/copilotkit/route.ts:10`,
  `export const runtime = "nodejs"`) — preserve this if the route is
  extended.
- **Weave tracing is not yet real instrumentation** — `weave.init()` runs,
  but there is no `@weave.op` nesting, no working `client.publish()`/flush,
  and no real per-call `ui_url`. A unified assistant should not assume its
  tool calls will show up as nested Weave spans until `weave_trace.py` is
  actually fixed (a pre-existing, separate task called out in AGENTS.md §4/§1
  as demo-critical for WS-A) — treat any "show it live in Weave" requirement
  as blocked on that fix, not as something the assistant work itself
  automatically provides.
- **Redis is standard `redis.asyncio` via `REDIS_URL` today, not Upstash
  REST** — `python/hearttwin/tools/redis_client.py:1-11` explicitly states
  *"This replaces the previous Upstash REST integration: DualBeat now talks
  to any standard Redis."* AGENTS.md §4's Upstash-REST-specific constraints
  (no `XREAD BLOCK` over REST, 32KB hash field limits, 500K commands/month
  free tier) **do not apply** to the current client; a real TCP/`rediss://`
  Redis connection has different limits and does support blocking ops. Any
  new assistant feature that wants Redis (session cache, conversation
  history, semantic cache) should target `redis_client.py`'s current
  `redis.asyncio` interface, not the Upstash REST API AGENTS.md describes.
- **Safety boundary is non-negotiable and duplicated across both stacks** —
  both `python/hearttwin/copilot.py` (`_check_output_safety`,
  `_OUTPUT_RED_FLAGS`) and CareGuard's copilot agent enforce
  diagnosis/treatment/emergency blocking independently. A unified assistant
  must preserve **both** safety gates (or a merged superset) — do not drop
  either check when consolidating.
- **`web/lib/api.ts` and CopilotKit actions currently call the pipeline
  through two different code paths** (REST client vs. direct orchestrator
  calls in `copilot.py`) that must be kept in sync manually. If the unified
  assistant adds more actions, prefer having it call the same orchestrator
  functions `copilot.py` already uses, to avoid a third, divergent code path.
- **Treat `AGENTS.md`, `docs/TASKS.md`, and `docs/PLANNING.md` as historical/
  partially stale for the frontend stack, CopilotKit wiring, Redis client,
  and deploy target** — verified-current facts from this audit (this file)
  should take precedence over those documents for those specific topics until
  a human reconciles them; AGENTS.md's safety rules (§1 rule 4), physics-core
  sacredness (§1 rule 3), and test-suite/secrets rules (§1 rules 5-6) remain
  fully authoritative and unaffected by this staleness.
