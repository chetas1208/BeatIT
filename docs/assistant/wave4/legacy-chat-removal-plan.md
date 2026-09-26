# Legacy Chat Surface Removal Plan (Wave 4 audit — for a LATER wave to execute)

> Status: **PLAN ONLY. Not executed. Do not act on this until every prerequisite
> in §4 is confirmed true.** Written by Agent 17 ("Legacy Chat Removal
> Engineer"), Wave 4, as a consolidation-readiness audit. No files under
> `web/components/{copilot,careguard,layout}/` or `python/` were modified to
> produce this document — see the "What this wave did / did not touch" note at
> the end.

## 0. Why this isn't happening yet

Per `docs/assistant/WAVE_3_HANDOFF.md`, the new unified pipeline
(`python/hearttwin/assistant/orchestrator.py`, `router.py`, `safety_validator.py`,
`tool_registry.py` / `physician_tools.py`) has **no LLM wired in** — every
non-blocked, non-tool-grounded question returns an honest
`UNSUPPORTED`/`INSUFFICIENT_EVIDENCE`, and `router.py` is **not even mounted**
into `python/hearttwin/api.py` yet (verified below, §4.1). Deleting
`CopilotDock.tsx` (real OpenAI-backed Q&A + full pipeline drive) or
`CareGuardCopilot.tsx` (real Anthropic-backed grounded analysis Q&A) today would
regress a working product to a strictly worse one. This plan is what a later
wave executes once the orchestrator can actually answer what these two surfaces
answer today.

## 1. Verified current mount sites (re-checked against live code, not copied from Wave 1)

All citations below were re-read directly from the working tree during this
wave (2026-09-26); Wave 1's `CHAT_SURFACE_AUDIT.md` citations for these same
lines are confirmed still accurate — nothing has drifted.

### CopilotDock (Cardiology Copilot — OpenAI, CopilotKit/AG-UI)

| Site | file:line | What's there |
|---|---|---|
| Provider root | `web/app/layout.tsx:4` | `import { CopilotProvider } from "@/components/copilot/CopilotProvider";` |
| Provider mount | `web/app/layout.tsx:42` | `<CopilotProvider>{children}</CopilotProvider>` — wraps the whole app in the CopilotKit React context (`<CopilotKit runtimeUrl="/api/copilotkit">`). This is a **separate** concern from CopilotDock itself: it must stay if *anything* (including a future unified panel) still uses CopilotKit hooks; it can go only if the unified panel drops CopilotKit entirely. |
| Page root | `web/app/page.tsx:1,9` | `import { AppShell } from "@/components/layout/AppShell"; ... return <AppShell />;` |
| Import | `web/components/layout/AppShell.tsx:28` | `import { CopilotDock } from "@/components/copilot/CopilotDock";` |
| CSS-hiding hack + mount | `web/components/layout/AppShell.tsx:186-191` | ```jsx\n{/* One copilot per surface: the CareGuard tab has its own dedicated\n    analysis copilot (CareGuardConsole -> CareGuardCopilot), so the\n    cardiac-twin CopilotDock is suppressed there to avoid two launchers. */}\n{tab !== "careguard" && (\n  <ErrorBoundary name="Cardiology Copilot"><CopilotDock /></ErrorBoundary>\n)}\n``` — the tab-conditional `{tab !== "careguard" && ...}` is the exact anti-pattern `AGENTS.md`/Wave 1 flags for replacement, not preservation. |
| Component definition | `web/components/copilot/CopilotDock.tsx:301` | `export function CopilotDock() {` (783-line file total) |

### CareGuardCopilot (CareGuard analysis copilot — Anthropic, plain REST)

| Site | file:line | What's there |
|---|---|---|
| Import | `web/components/careguard/CareGuardConsole.tsx:6` | `import { CareGuardCopilot } from "@/components/careguard/CareGuardCopilot";` |
| Mount | `web/components/careguard/CareGuardConsole.tsx:527` | `<CareGuardCopilot caseId={caseId} />` |
| Component definition | `web/components/careguard/CareGuardCopilot.tsx:14` | `export function CareGuardCopilot({ caseId }: { caseId: string }) {` (104-line file total) |
| Feature flag gate | `web/components/layout/AppShell.tsx:58`, `web/lib/careguardApi.ts:22` | `NEXT_PUBLIC_CAREGUARD_ENABLED` — CareGuard's whole tab (and therefore `CareGuardCopilot`) only renders when this is `"true"`; unaffected by this plan. |

No other import/JSX reference to either component exists anywhere under
`web/` (`grep -rn "CopilotDock\|CareGuardCopilot" web/` returns exactly the
six lines above plus one doc-comment mention in
`web/components/copilot/CopilotProvider.tsx:11`, which is a comment, not code).

## 2. Exact `AppShell.tsx` diff for a future wave

Two changes, both in `web/components/layout/AppShell.tsx`:

**(a) Remove the import (line 28):**
```diff
-import { CopilotDock } from "@/components/copilot/CopilotDock";
```

**(b) Replace the CSS-hiding block (lines 186-191) with an unconditional mount of the unified panel:**
```diff
-      {/* One copilot per surface: the CareGuard tab has its own dedicated
-          analysis copilot (CareGuardConsole -> CareGuardCopilot), so the
-          cardiac-twin CopilotDock is suppressed there to avoid two launchers. */}
-      {tab !== "careguard" && (
-        <ErrorBoundary name="Cardiology Copilot"><CopilotDock /></ErrorBoundary>
-      )}
+      {/* Single unified assistant, mounted unconditionally — replaces the old
+          per-tab CopilotDock/CareGuardCopilot split (Wave 1 finding, executed
+          per docs/assistant/wave4/legacy-chat-removal-plan.md). It reads the
+          active tab/case itself and needs no tab-conditional hide. */}
+      <ErrorBoundary name="Assistant"><UnifiedAssistantPanel /></ErrorBoundary>
```
plus a new import near line 28:
```diff
+import { UnifiedAssistantPanel } from "@/components/assistant/UnifiedAssistantPanel";
```

**Component name/path caveat (per task instructions):** at the time this audit
was written, Agent 16's unified panel had **not yet landed** in the tree —
`find web/components -iname "*unified*" -o -iname "*assistant*"` and
`grep -rn "UNIFIED_ASSISTANT" web/ python/ docs/` both returned nothing. The
name `UnifiedAssistantPanel` at `@/components/assistant/UnifiedAssistantPanel`
above is a **placeholder following the codebase's existing naming convention**
(`CopilotDock`, `CareGuardConsole` — `<Domain><Role>` PascalCase, one component
per file under `web/components/<domain>/`). **A future wave executing this
plan must first run** `grep -rn "UnifiedAssistantPanel\|isUnifiedAssistantEnabled" web/components web/lib`
**to find Agent 16's actual component name/path and substitute it above before
touching `AppShell.tsx`.**

**(c) CareGuardConsole.tsx:6,527** — no change needed *if* the unified panel is
meant to also cover CareGuard's grounded-analysis Q&A (per this plan's
intent). If so, delete both lines:
```diff
-import { CareGuardCopilot } from "@/components/careguard/CareGuardCopilot";
```
```diff
-      <CareGuardCopilot caseId={caseId} />
```
so CareGuard relies solely on the one global `UnifiedAssistantPanel` mounted
in `AppShell.tsx`, the same way the main console does today.

**(d) `CopilotProvider` (`web/app/layout.tsx:4,42`)** — leave in place unless
the unified panel is confirmed to need zero CopilotKit hooks. Removing it
prematurely would break anything still relying on the CopilotKit React
context. Decide this at execution time by checking what Agent 16's panel
actually imports.

## 3. Backend logic: what to delete (UI) vs. keep/migrate (logic)

**Delete only the UI-facing wiring that exists purely to serve the two
components above. Do NOT delete the deterministic/Anthropic logic itself —
re-wrap it as tools.**

### `python/hearttwin/copilot.py` (5 CopilotKit actions)

| Action | Verdict | Why |
|---|---|---|
| `create_case`, `extract`, `operate`, `simulate_recovery` | **Keep the logic, retire the CopilotKit `Action` wrapper.** These call `run_extraction_pipeline`/`run_operation_pipeline`/`run_recovery_pipeline` directly — pure passthroughs to the sacred deterministic pipeline (`orchestrator.py`), no LLM involved. The orchestrator's `tool_registry.py`/`physician_tools.py` should get equivalent tools (if not already covered) so the unified assistant can still drive the pipeline. |
| `answer_case_question` | **Keep the logic, do not discard the OpenAI call wholesale** — but it must be re-evaluated once the orchestrator has real LLM routing (Wave 6+). Its safety checks (`_check_output_safety`, `_OUTPUT_RED_FLAGS`) are already unioned into `safety_validator.check_output_safety` (verified §5) — that part is already done, nothing to migrate there. |
| `_OUTPUT_RED_FLAGS` constant | **Do not delete even after UI removal.** `python/hearttwin/assistant/safety_validator.py:53` imports it live (`from python.hearttwin.copilot import _OUTPUT_RED_FLAGS`). Deleting `copilot.py` outright would break the unified validator's import. If `copilot.py` is ever fully retired, this constant must be relocated (e.g. into `safety_validator.py` itself or a shared `safety_constants.py`) **before** the file is deleted, with the import updated in the same change. |
| `add_fastapi_endpoint(app, sdk, "/copilotkit")` mount (`python/hearttwin/api.py:122` per Wave 1; re-verify line at execution time — `api.py` is Codex's active file) | **Retire once `CopilotProvider`/`CopilotDock` are gone and nothing else calls `/copilotkit`.** Confirm no other frontend caller of `/api/copilotkit` exists first (`grep -rn "copilotkit" web/`). |

### `python/hearttwin/careguard/copilot_agent.py`

| Piece | Verdict | Why |
|---|---|---|
| `answer()` / `_deterministic_answer()` grounded-analysis logic | **Keep, migrate.** Re-wrap as a tool in `python/hearttwin/assistant/tool_registry.py` or `physician_tools.py` (e.g. `answer_careguard_question`) so the unified assistant can still answer "why flagged / what alternative / what's missing / critic verdict" questions grounded in CareGuard's Redis artifacts (`careguard/memory/keys.py`). This mirrors Wave 1's own Recommendation 1. |
| `_BLOCK` constant | **Do not delete even after UI removal**, same reasoning as `_OUTPUT_RED_FLAGS` above — `safety_validator.py:52` imports it live (`from python.hearttwin.careguard.copilot_agent import _BLOCK as _CAREGUARD_BLOCK`). Relocate-then-delete if `copilot_agent.py` is ever fully retired, updating the import atomically. |
| Anthropic client usage (`careguard/anthropic/client.py`) | **Keep.** Model routing (Haiku/Sonnet/Fable by stage) is real infrastructure, reusable by whatever tool replaces `answer()`. |
| `POST /cases/{case_id}/copilot` route (`python/hearttwin/careguard/routes_analysis.py:50-55`) | **Retire the route once `CareGuardCopilot.tsx` is deleted and nothing else calls it** — but **first port its `audit.record(...)` call** (routes_analysis.py:53-54) into whatever new tool/handler answers these questions in the unified pipeline. CareGuard's audit trail is a named deliverable (`docs/careguard/architecture.md`) and tests assert on it (per Wave 1 Recommendation 5) — do not drop it silently. |
| `DISCLAIMER` string (`copilot_agent.py:22`, `"Clinical decision support draft. Clinician review required."`) | **Decision needed at execution time, not resolved by this plan** (per Wave 1 Recommendation/WAVE_1_HANDOFF item 4): does the unified assistant use `safety.py`'s `DISCLAIMER`/`CORE_SAFETY_PHRASE` for everything, or keep a CareGuard-specific variant for CareGuard-sourced answers? `safety_validator.py:70` currently defers this same question (`REQUIRED_SAFETY_DISCLAIMER = DISCLAIMER`, comment explicitly flags it as unresolved). |

## 4. Prerequisites — all must be true before this plan is safely executable

1. **`router.py` must be mounted into `api.py`.** Verified now: it is **not**
   (`grep -n "assistant" python/hearttwin/api.py` returns nothing). This is
   Wave 3 Handoff's own next-step item 1 and blocks everything downstream —
   there is no live endpoint for a frontend to call yet.
2. **Orchestrator must have LLM routing for at least the intent categories
   these two surfaces currently cover**, per `WAVE_3_HANDOFF.md`'s "What was
   implemented" §1: today "No LLM call exists anywhere in this path... every
   non-blocked, non-clarification response is either a real tool result or an
   honest `UNSUPPORTED`." Concretely still missing per that same handoff:
   - Open-ended case Q&A of the kind `answer_case_question` (OpenAI) and
     CareGuard's `answer()` (Anthropic) both do today — free-text reasoning
     over already-computed state, not just a fixed tool call.
   - The `case_id`/`patient_id` schema mismatch (§ "Architecture decisions" in
     `WAVE_3_HANDOFF.md`) currently makes `get_cardiac_findings`/
     `get_pv_loop`/`get_raw_provenance_ledger`/`get_findings_by_region`
     **unreachable** through the orchestrator — must be resolved so the
     unified assistant can answer what CareGuard's grounded-analysis
     questions need.
3. **CareGuard's Q&A logic must be ported into a tool** (§3 above) —
   `answer_careguard_question` or equivalent — and reachable by the
   orchestrator, with the audit-log call preserved.
4. **The pipeline-driving actions** (`create_case`/`extract`/`operate`/
   `simulate_recovery`) must have orchestrator-reachable equivalents so the
   unified panel can still drive the full pipeline, not just answer questions.
5. **Agent 16's unified panel component must exist, be mounted behind
   `NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED`, and have been run enabled in a
   real environment** long enough to build confidence it doesn't regress the
   demo — before flipping it on by default and deleting the fallback.
6. **The `safety_validator.py` "clinical" word false positive** flagged in
   `WAVE_3_HANDOFF.md` ("A safety-validator false positive found and locally
   handled — needs Wave 4 review") should get a proper allowlist fix before
   this removal, since post-removal there is no second surface left to fall
   back on if the unified validator over-blocks.
7. **Full test suite green** (`pnpm test:py` / `pnpm check`) both before and
   after the removal PR, with new tests covering whatever replaces
   `CopilotDock`'s and `CareGuardCopilot`'s behavior.
8. **Disclaimer-string decision made** (§3 table, last row) rather than left
   as an open TODO — the union-safety validator already depends on knowing
   which disclaimer is canonical.

## 5. Independent verification: both legacy safety blocklists are covered by the unified validator

Re-verified fresh this wave (not citing Wave 2's own claim about itself) by
reading all three files directly:

- **`python/hearttwin/copilot.py:59-74`** — `_OUTPUT_RED_FLAGS` is a 14-item
  tuple (`"you should see a doctor about"`, `"you should take"`, `"i recommend
  you take"`, `"i recommend taking"`, `"you need to take"`, `"start taking"`,
  `"stop taking"`, `"your diagnosis is"`, `"you have been diagnosed"`, `"the
  recommended treatment"`, `"recommended treatment is"`, `"you should be
  treated"`, `"prescribe"`, `"milligrams"`).
- **`python/hearttwin/careguard/copilot_agent.py:24-25`** — `_BLOCK` is an
  8-item tuple (`"what should i take"`, `"what do i take"`, `"should i stop"`,
  `"prescribe me"`, `"what dose"`, `"how many mg"`, `"diagnose me"`, `"am i
  going to"`).
- **`python/hearttwin/assistant/safety_validator.py:52-53`** imports **both,
  live, by name**, not copied:
  ```python
  from python.hearttwin.careguard.copilot_agent import _BLOCK as _CAREGUARD_BLOCK
  from python.hearttwin.copilot import _OUTPUT_RED_FLAGS
  ```
  and `check_output_safety()` (lines 362-406) iterates both lists against the
  candidate text (`for phrase in _OUTPUT_RED_FLAGS: ...` at line 384; `for
  phrase in _CAREGUARD_BLOCK: ...` at line 388), plus layers on
  `check_request_safety`'s shared regex matcher and
  `validate_simulation_outputs` — i.e. the union is a strict superset of
  either original surface's own check, and because the imports are live
  (not string-literal copies), a future edit to either source list is picked
  up automatically with no drift risk.

**Conclusion: confirmed independently — both legacy blocklists are present
and enforced in the unified validator, via live import, as of this wave.**
No gap found. (`copilot.py`'s `_check_output_safety` also layers
`check_request_safety`/`_BLOCKED_PATTERNS` from `safety.py` and
`validate_simulation_outputs` on top of `_OUTPUT_RED_FLAGS` — both of those
are separately imported into `safety_validator.py` too, lines 54-60, so that
coverage carries over as well.)

## 6. Rollback note

Because this wave makes **no destructive change** to either legacy surface —
`CopilotDock.tsx`, `CareGuardCopilot.tsx`, `CopilotProvider.tsx`,
`AppShell.tsx`, `CareGuardConsole.tsx`, and every backend file behind them are
completely untouched — there is nothing to "roll back" yet. This note is for
**after** a future wave executes §2/§3 of this plan and ships the unified
panel as default-on:

- If the unified panel has a critical bug post-launch, re-enabling the legacy
  surfaces is a **pure revert** of that future wave's `AppShell.tsx` diff
  (§2) plus restoring the two deleted imports/JSX blocks — trivial with
  `git revert <that-PR's-merge-commit>` since this plan calls for one
  self-contained diff, not a scattered one. Because backend logic (§3) is
  *migrated*, not deleted, and the `_OUTPUT_RED_FLAGS`/`_BLOCK` constants
  must not be deleted until fully retired (§3), a revert of the frontend
  mount alone is sufficient — no backend rollback should be needed unless the
  future wave also deleted `copilot.py`/`copilot_agent.py` outright, which
  this plan explicitly advises against doing in the same change as the UI
  removal.
- Feature-flag rollback is even faster in the interim: while both
  `NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED` (new, see
  `web/lib/assistant/unifiedAssistantFlag.ts`) and the legacy surfaces
  coexist (i.e. before this plan's §2/§3 are executed), simply setting
  `NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED=false` (or leaving it unset) fully
  reverts user-visible behavior to today's two-surface state with **zero code
  changes**, since Agent 16's panel is additive and off by default this wave.

## What this wave did / did not touch

**Did:** read (not edit) `CopilotDock.tsx`, `CareGuardCopilot.tsx`,
`AppShell.tsx`, `CareGuardConsole.tsx`, `CopilotProvider.tsx`,
`web/app/layout.tsx`, `web/app/page.tsx`, `python/hearttwin/copilot.py`,
`python/hearttwin/careguard/copilot_agent.py`,
`python/hearttwin/assistant/safety_validator.py`,
`docs/assistant/{CHAT_SURFACE_AUDIT.md,WAVE_1_HANDOFF.md,WAVE_3_HANDOFF.md}`;
ran `git status`/`git log` and greps only. Wrote this plan document and one
new, non-colliding helper file, `web/lib/assistant/unifiedAssistantFlag.ts`
(new file, not wired into anything).

**Did not:** edit `AppShell.tsx`, `CopilotDock.tsx`, `CareGuardCopilot.tsx`,
`CareGuardConsole.tsx`, `CopilotProvider.tsx`, or anything under `python/`.
No legacy surface was disabled, hidden further, or altered in any way.

**Observed but not touched (Codex activity, per `git status` at the start of
this wave):** uncommitted modifications to `Decisions.md`, `Progress.md`,
`README.md`, `docs/credibility/*`, `docs/hackathon/M5_5_*`/`M6_*`/`M7_*`,
`python/hearttwin/api.py`, `python/hearttwin/ensemble.py`,
`scripts/benchmark_ensemble.py`, `scripts/verify_env.py`,
`web/components/heart/HeartScene.tsx`,
`web/components/twin/scenario/ScenarioPanel.tsx`, `web/lib/api.ts`,
`web/package.json`, plus untracked Shadow Trial files
(`python/hearttwin/shadow_trial_*.py`, `storage/shadow_trial_store.py`,
`fixtures/golden/shadow_trials/`) and several new `docs/hackathon/M6_*`/`M7_*`
docs. None of these overlap this wave's two deliverables. Notably,
`python/hearttwin/api.py` is mid-flux under Codex — §3/§4 above both flag that
its exact `/copilotkit` mount line and `router.py` mount status must be
re-verified at execution time, not assumed from this document.
