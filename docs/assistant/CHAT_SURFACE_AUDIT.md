# Chat / Assistant Surface Audit

Scope: pure discovery, no code changes. Evidence-based, file:line cited. Read
first: root `README.md`, `Progress.md`, `Decisions.md`, `web/AGENTS.md`,
`docs/careguard/architecture.md`, `docs/careguard/anthropic-integration.md`,
`docs/TASKS.md`, `docs/PLANNING.md`.

## Summary

**Count: TWO distinct, simultaneously-active chat surfaces today** (not zero,
not one). A third, older plan (a Nuxt/Vue frontend with a React-island
CopilotKit widget, described in `docs/PLANNING.md:158-161` and
`docs/TASKS.md:161-192`) is **fully superseded** — there is no `app/` Nuxt
directory left anywhere in the repo (`find . -maxdepth 2 -iname app` returns
only `web/app`, the Next.js App Router tree), so it is dead planning text, not
dead code.

The two live surfaces are architecturally unrelated: (1) **"Cardiology
Copilot"** (`web/components/copilot/CopilotDock.tsx`) is a real CopilotKit
(AG-UI) integration — `useCopilotReadable`/`useCopilotAction`/
`renderAndWaitForResponse`, backed by `/copilotkit` on the FastAPI app,
OpenAI-driven — mounted globally in `AppShell` and shown on the main BeatIT
console (twin/simulation tabs). (2) **"CareGuard analysis copilot"**
(`web/components/careguard/CareGuardCopilot.tsx`) is a hand-rolled floating
chat widget (plain `useState` thread, no CopilotKit) that calls a plain REST
endpoint (`POST /api/v1/careguard/cases/{id}/copilot`), Anthropic-driven, and
is shown only inside the CareGuard console/tab. `AppShell.tsx` explicitly
suppresses surface (1) when the CareGuard tab is active specifically **to
avoid showing two launchers at once** (`web/components/layout/AppShell.tsx:186-191`),
which is direct in-repo acknowledgment that the fragmentation is already a
known problem the team papered over with a visibility toggle rather than a
real merge. Both surfaces read from different backends, different model
providers, different state stores, and different disclaimer strings
(`DISCLAIMER` in `python/hearttwin/safety.py` vs `DISCLAIMER =
"Clinical decision support draft. Clinician review required."` in
`python/hearttwin/careguard/copilot_agent.py:22`), so today the user sees two
different "copilots" with two different personalities depending only on which
tab is focused.

## Surfaces Found

| Route / page | Component (file:line) | Purpose (one line) | Backend endpoint(s) | Model / LLM | State | Status |
|---|---|---|---|---|---|---|
| `/` (main console, "Digital Twin" / "Physiology Simulation" tabs) | `web/components/copilot/CopilotDock.tsx:301` (mounted by `web/components/layout/AppShell.tsx:28,190`) | "Cardiology Copilot" — drives the pipeline (create_case → extract → operate → simulate_recovery) and answers case questions via generative-UI cards + one human-in-the-loop confirm step | `/copilotkit` (CopilotKit AG-UI actions), proxied by `web/app/api/copilotkit/route.ts:1-99` to backend `add_fastapi_endpoint(app, sdk, "/copilotkit")` (`python/hearttwin/api.py:122`) | OpenAI via `python/hearttwin/intelligence/factory.py` (`answer_case_question` only — the sole LLM-backed action, `python/hearttwin/copilot.py:451-530`); other actions (`create_case`/`extract`/`operate`/`simulate_recovery`) call the deterministic pipeline directly, no LLM | Global: CopilotKit's own runtime message history (client-side, per `<CopilotKit>` provider in `web/components/copilot/CopilotProvider.tsx:39-47`) + case state read from `useDualBeatStore` (`web/lib/store.ts`) via `useCopilotReadable` (`CopilotDock.tsx:361-367`); case record persisted server-side via `store_case`/Redis or in-memory fallback (`python/hearttwin/tools/storage.py:1-21`) | **Active** — wired into the default app shell, backed by real actions and a real endpoint |
| `/careguard`, `/careguard/runner`, `/careguard/cases`, and the "CareGuard" tab inside `/` (when `NEXT_PUBLIC_CAREGUARD_ENABLED=true`) | `web/components/careguard/CareGuardCopilot.tsx:14-95`, rendered from `web/components/careguard/CareGuardConsole.tsx:6,527` | "CareGuard analysis copilot" — answers grounded analysis questions (why flagged, what alternative, what's missing, critic verdict) about the loaded CareGuard case artifacts; explicitly refuses dosing/self-treatment questions | `POST /cases/{case_id}/copilot` under the CareGuard router base (`web/lib/careguardApi.ts:120-123`, `python/hearttwin/careguard/routes_analysis.py:50-55`) → `python/hearttwin/careguard/copilot_agent.py:71` `answer()` | Anthropic (`python/hearttwin/careguard/anthropic/client.py`, model routing in `docs/careguard/anthropic-integration.md:8-13`: Haiku/Sonnet/Fable by stage) when `client.is_available()`, else a deterministic keyword-based answer (`copilot_agent.py:_deterministic_answer`) | Local component state only: `useState<Turn[]>([])` (`CareGuardCopilot.tsx:18`) — **chat turns are not persisted**, lost on remount/refresh. Grounding data is pulled fresh per-question from Redis (`case_context`, `case_guidelines`, `case_contraindications`, etc. — `python/hearttwin/careguard/memory/keys.py:17-33`) | **Active**, but feature-flag gated (`CAREGUARD_ENABLED` backend / `NEXT_PUBLIC_CAREGUARD_ENABLED` frontend, `docs/careguard/architecture.md:9-13`) — off by default in a bare checkout |
| (superseded) legacy Nuxt/Vue `app/` frontend with a planned "React island" CopilotKit widget | none present — described only in `docs/PLANNING.md:158-161` and `docs/TASKS.md:161-192` | Planning-stage idea for embedding CopilotKit into a Vue app before the team instead migrated the whole frontend to Next.js | n/a | n/a | n/a | **Dead planning text, not code** — no `app/` directory exists anywhere in the repo (`find . -maxdepth 2 -iname app` → only `web/app`); `Progress.md:64` still lists "keep the legacy frontend runner quarantined or remove it" as an open action item, but that refers to `web/lib/twin/ensemble/runner.ts` (a client-side ensemble calculator no longer imported by production code, per `docs/hackathon/M5_5_FRONTEND_QUARANTINE.md:1-24`), **not** a chat surface |

Note on naming: nothing in the repo is a distinct "physician panel" or
"PhysicianMode" UI. `CareGuardConsole.tsx` / `CareGuardCopilot.tsx` are the
closest analog — the word "clinician" appears 40+ times across
`python/hearttwin/careguard/**` (constants, disclaimers, schemas) as the
target-user framing for that whole feature, not as a separate UI mode. There
is no code-level split between a "physician view" and a general view beyond
the CareGuard flag/tab itself.

## Backend Conversation Endpoints

| Endpoint | File:line | Mechanism | Conversation state store |
|---|---|---|---|
| `/copilotkit` (`/copilotkit/info`, `/copilotkit/actions/execute`) | `python/hearttwin/api.py:35,122`; actions defined in `python/hearttwin/copilot.py:538-657` | CopilotKit `add_fastapi_endpoint` / `CopilotKitRemoteEndpoint` (AG-UI protocol) | No server-side turn history. Each action call loads/saves a `CaseRecord` via `get_case`/`store_case` (`python/hearttwin/tools/storage.py`) — Redis-backed when `REDIS_URL` is set, else a module-level `_MEMORY_STORE: dict` (`storage.py:20`, in-memory, lost on restart). Message-level chat history lives only in the CopilotKit client runtime (browser), not server-persisted. |
| `POST /api/v1/careguard/cases/{case_id}/copilot` | `python/hearttwin/careguard/routes_analysis.py:50-55` | Plain FastAPI REST route (no CopilotKit) | No turn history at all, server or client-persisted beyond the current page session (`CareGuardCopilot.tsx` React state). Each call re-reads current case artifacts from Redis under `careguard:case:{case_id}:*` keys (`python/hearttwin/careguard/memory/keys.py:17-33`) and writes one audit-log line via `audit.record(...)` (`routes_analysis.py:53-54`) — that audit trail records *that* a question was asked and whether Anthropic was used, not the question/answer text itself. |

No other route matching `/chat`, `/conversation`, `/assistant`, or `/message`
exists anywhere under `python/hearttwin/**` or `api/**`
(`grep -rniE '"/chat|/conversation|"/message'` over both trees returns only
the CareGuard `APIRouter(prefix=...)` declaration line, no route decorators).
`api/index.py:1-3` is a 3-line re-export of the FastAPI app; it defines no
routes of its own.

## Duplication Risks

1. **Two "copilot" mental models for one user.** A clinician using BeatIT
   end-to-end sees a slick CopilotKit chat with generative UI + confirm
   dialogs on the main tabs, then a visually distinct hand-styled bubble
   widget the moment they open CareGuard — different fonts/colors (inline
   `style` objects in `CareGuardCopilot.tsx:97-104` vs the themed
   `CopilotChat`/`ht-panel` classes in `CopilotDock.tsx`), different
   disclaimer wording, different capabilities (one drives the whole pipeline,
   the other only answers Q&A).
2. **Two backend "copilot" modules with overlapping names but incompatible
   contracts**: `python/hearttwin/copilot.py` (CopilotKit actions, OpenAI) and
   `python/hearttwin/careguard/copilot_agent.py` (plain REST handler,
   Anthropic). Anyone searching the codebase for "the copilot" will find both
   and must read carefully to know which one backs which UI — there is no
   shared base class, shared prompt-safety helper, or shared disclaimer
   constant between them (`CORE_SAFETY_PHRASE`/`DISCLAIMER` in `safety.py` vs.
   the CareGuard-local `DISCLAIMER` string literal in `copilot_agent.py:22`).
3. **Suppression instead of consolidation.** `AppShell.tsx:186-191` hides
   `CopilotDock` when the CareGuard tab is open "to avoid two launchers" — this
   is a tell that the team already recognized users could otherwise see both
   floating buttons simultaneously in the same viewport, and chose a
   tab-conditional hide rather than a single entry point.
4. **Inconsistent conversation durability.** Neither surface persists chat
   turns server-side. The CopilotKit surface at least keeps history in the
   CopilotKit client runtime for the duration of the tab session; the
   CareGuard widget's `turns` state is plain React `useState` inside a
   component that unmounts whenever the user leaves `/careguard` or switches
   the AppShell tab away and back (the tab switch in `AppShell.tsx` does not
   unmount `CareGuardConsole`'s subtree per se, since it's conditionally
   rendered in the JSX — switching tabs does remount it, so history is lost on
   every tab round-trip). A unified surface would need one decision about
   where turns live.
5. **Different safety-boundary implementations doing the same job.** Both
   surfaces independently re-implement "refuse to prescribe/diagnose/dose"
   logic — `_OUTPUT_RED_FLAGS` + `_check_output_safety` in `copilot.py:59-74,418-448`
   vs. the keyword tuple `_BLOCK` in `careguard/copilot_agent.py:26-27`. A
   consolidation effort must not silently drop either safety gate; today they
   catch different phrasings.
6. **Two different "case" identities in play.** The main copilot's `case_id`
   comes from `useDualBeatStore` (DualBeat pipeline cases); the CareGuard
   copilot's `caseId` prop comes from CareGuard's own case/run flow
   (`routes_case.py`, `routes_runs.py`). They are not the same ID space and a
   unified assistant would need to decide which case model is canonical, or
   how to bridge them (the existing read-only `hearttwin_adapter.py` bridge
   only carries physiology parameters, not case identity/conversation
   context).

## Recommendations for Consolidation

1. **Pick one CopilotKit runtime as the single chat surface** — the CopilotKit
   integration (`CopilotDock` + `/copilotkit`) is the more capable and more
   "load-bearing" one for the sponsor-prize framing in root `AGENTS.md`
   (generative UI + human-in-the-loop already implemented there, required by
   `AGENTS.md` §5 Definition of Done for the CopilotKit prize). Migrating
   CareGuard's Q&A into a `answer_careguard_question`-style CopilotKit action
   (mirroring `answer_case_question` in `python/hearttwin/copilot.py:451`) —
   backed by the existing Anthropic-driven `copilot_agent.answer()` logic —
   would fold both into one chat window without discarding CareGuard's
   grounding or refusal behavior.
2. **Unify on one entry point, one launcher button.** Whatever surface wins,
   `AppShell.tsx`'s current tab-conditional suppression
   (lines 186-191) should become unnecessary — a single dock that is
   context-aware (reads whichever case/tab is active via
   `useCopilotReadable`) rather than two components that must be manually kept
   from colliding.
3. **Reconcile disclaimers and safety gates before merging**, not after —
   both `_check_output_safety`/`_OUTPUT_RED_FLAGS` (`copilot.py`) and `_BLOCK`
   (`copilot_agent.py`) encode real, tested safety behavior
   (`test_careguard_isolation.py`, `test_safety_language.py`); a merge must
   take the union of both blocklists rather than picking one file to keep.
4. **Decide the case-identity bridge explicitly.** A unified assistant needs
   one of: (a) two `case_id` namespaces the copilot switches between based on
   active view, or (b) a shared case identity across DualBeat and CareGuard.
   This is a design decision for a later wave, not something to guess at here.
5. **If CareGuard's REST endpoint is retired**, keep
   `python/hearttwin/careguard/routes_analysis.py`'s audit-logging behavior
   (`audit.record(...)`) — CareGuard's audit trail is a named deliverable in
   `docs/careguard/architecture.md` and several tests assert on it; folding
   the Q&A into a CopilotKit action must still call `audit.record` on each
   turn.
6. **Update the stale foundation doc** — `web/components/README.md:19` still
   lists `components/safety/SafetyBanner.tsx` as a protected foundation file,
   but the actual component is `components/safety/DisclaimerModal.tsx`
   (confirmed via `AppShell.tsx:20,185`). Not a chat surface, but worth fixing
   alongside any consolidation PR so future agents don't chase a nonexistent
   file.
