# Physician Helper UI Cleanliness Audit (Wave 6.5)

> Deliverable of the "UI Cleanliness Auditor" role, per
> `docs/assistant/PHYSICIAN_HELPER_HARDENING.md` §4 (highest-priority target 5:
> "Zero UI implementation leakage") and its scheduled-wave item 4. Full spec
> sections §38-§57 / §81-§86 referenced by that task were not found as a
> standalone document in the repo (only the condensed
> `PHYSICIAN_HELPER_HARDENING.md` summary exists) — this audit was run against
> that summary's hard rule plus the task's own inline restatement of the
> §45 vocabulary guide and §83-§85 examples.

**Scope audited:** the two existing, live chat surfaces
(`web/components/copilot/CopilotDock.tsx`,
`web/components/careguard/CareGuardCopilot.tsx`) and the seven Wave 4
`web/components/assistant/*.tsx` files
(`BeatITCopilotPanel`, `BeatITCopilotTrigger`, `ArtifactCard`,
`PhysicianBriefView`, `ArtifactDetailPanel`, `SuggestedActionChips`,
`VisuallyHidden`). The rest of `web/` was grepped for the same leak patterns
to characterize the wider picture, but only the nine files above were
in-scope to *fix* this wave.

**Explicitly out of scope, not touched, not audited in depth:** everything
under `web/components/twin/shadow-trial/`, `web/components/twin/comparison/`,
`web/components/twin/missing-piece/`, `web/lib/twin/comparison/` — confirmed
present and active via `git status`/`find` at the start of this wave (Codex's
in-progress work, uncommitted). A future pass must audit these once they are
stable/committed. Also not touched per the task's file-ownership constraints:
`AppShell.tsx`, `HeartScene.tsx`, `ScenarioPanel.tsx`, `web/lib/api.ts`,
`web/package.json`, anything under `python/`.

---

## Method

1. Read `docs/assistant/PHYSICIAN_HELPER_HARDENING.md` in full (147 lines —
   the only file in the repo containing the hard rule; no separate
   104-section spec file exists under `docs/`).
2. Read `docs/assistant/wave4/legacy-chat-removal-plan.md` (275 lines) for
   context on the two legacy surfaces' contracts and mount sites.
3. Read all 7 `web/components/assistant/*.tsx` files and both legacy chat
   components in full.
4. Grepped the whole `web/` tree (excluding `node_modules`, `.next`, and the
   three Codex-owned directories above) for: `/api/`, `localhost`, literal
   `POST`/`GET`/`PUT`/`DELETE`, `WebSocket`/`SSE`, `model=`/`provider=`/model
   vendor names (`gpt-4`, `claude-`, `anthropic`, `openai`, `nvidia`), the
   words `agent`/`worker`/`tool_call`/`trace_id`/`request_id`/`debug`, and
   `JSON.stringify` usage — then manually triaged every hit into
   code-comment/type-name (ignore), system-prompt/non-rendered (ignore),
   dev-only (leave), or genuinely user-facing (fix candidate).
5. Traced two render-site leaks back to their source to confirm they were
   real (`careguardApi.ts`'s thrown `Error` message, `assistantApi.ts`'s
   `AssistantApiError` message) before fixing at the render site.
6. Ran `git status` before and after every edit; ran `npx tsc --noEmit` and
   `npx eslint` on every touched file.

---

## Findings

### FIXED (real leaks, in my 9 in-scope files, string-literal-only fixes)

| # | File:line (pre-fix) | Leak | Category | Fix |
|---|---|---|---|---|
| 1 | `web/components/careguard/CareGuardCopilot.tsx:28` | `via: res.copilot.used_anthropic ? "Claude" : "deterministic"` rendered verbatim in the chat transcript (`via {t.via}` at line 69) | Model/provider name (Anthropic's product name "Claude") shown directly to the physician | `"Claude"` → `"AI-assisted"`, `"deterministic"` → `"Case rules"` |
| 2 | `web/components/careguard/CareGuardCopilot.tsx:32` | `a: \`Error: ${(e as Error).message}\`` — renders the raw thrown error's `.message` in the chat thread. Traced to `web/lib/careguardApi.ts:37`: `throw new Error(\`CareGuard ${res.status}: ${detail}\`)`, i.e. an HTTP status code plus backend `detail`/`statusText` gets displayed verbatim (e.g. `Error: CareGuard 500: Internal Server Error`) | HTTP status code + raw backend error text in ordinary chat UI | Replaced with a static clinical-safe message: `"Unable to complete this analysis right now. Please try again."`; catch binding `(e)` dropped since it's no longer read |
| 3 | `web/components/assistant/BeatITCopilotPanel.tsx:96-103` | Non-404 error path fell through to `cause instanceof Error ? cause.message : ...`. Traced to `web/lib/assistantApi.ts:37`: `super(\`[${args.status}] /assistant/message: ${args.detail}\`)` — the literal backend route `/assistant/message` plus an HTTP status code gets rendered directly in the assistant's chat notice for any non-404 failure (500s, network errors with status 0, etc.) | Backend route path + HTTP status code in ordinary chat UI — the single clearest hit against the hard rule's first two forbidden categories | Removed the `cause.message` branch entirely; non-404 `AssistantApiError` (and any other error) now renders the static `"The assistant couldn't complete this request. Please try again."` The pre-existing, already-safe 404 message ("still warming up — this feature isn't connected yet") was left untouched — it names no route, verb, or status. |
| 4 | `web/components/copilot/CopilotDock.tsx:247` | `Streaming agent telemetry` — a literal, rendered inside `RunningRows`, shown to the physician while a generative-UI card is mid-stream | Literal word "agent" (+ "telemetry", implementation-flavored) in a user-facing progress string | `"Streaming agent telemetry"` → `"Streaming simulation data"` (uses the preferred vocabulary's "Simulation") |
| 5 | `web/components/assistant/ArtifactDetailPanel.tsx:33-36` | `RawPayloadFallback`'s notice: `"— no backend generator produces a typed payload for this type yet (Wave 4). Showing the raw payload data below instead of a real view."` | Internal wave/roadmap numbering ("Wave 4") and backend-implementation phrasing ("no backend generator produces a typed payload") shown directly in a physician-facing artifact panel | Reworded to `"A formatted view is not yet available for this evidence type — showing the available case data below instead of a formatted view."` (dropped "Wave 4" and "backend generator"; kept the honest "not yet available" framing per the file's own "never fabricate" contract) |

All five fixes are pure string-literal swaps at the render site (or, for #2/#3,
dropping a dynamic-string branch in favor of a static one — no change to
control flow, conditions, props, or data flow otherwise). `npx tsc --noEmit`
and `npx eslint` on all four touched files (`CareGuardCopilot.tsx`,
`BeatITCopilotPanel.tsx`, `CopilotDock.tsx`, `ArtifactDetailPanel.tsx`) both
produced **zero output** (clean pass) after the edits.

### LEFT ALONE — found, but not safely fixable as a pure string-literal edit this wave

| # | File:line | Leak | Why not fixed now |
|---|---|---|---|
| 6 | `web/components/assistant/ArtifactDetailPanel.tsx:47` | `{typeof value === "string" ? value : JSON.stringify(value, null, 2)}` — raw JSON dumped into the artifact detail view for any of the 6 artifact types with no real generator yet | This is a genuine "raw JSON rendered directly to a user-facing element" hit, but removing it requires a real replacement view/behavior (a logic change), not a text swap. The immediately-adjacent leaked *text* around it (finding #5) was fixed; the raw-JSON *rendering itself* needs a proper follow-up (e.g. a generic key→friendly-label formatter, or hiding non-string values) — flagged for the report-personalization/artifact-viewer follow-up wave. |
| 7 | `web/components/copilot/CopilotDock.tsx:395-398`, `:584` and `web/components/careguard/CareGuardCopilot.tsx:54` | `newCaseId.slice(0, 8)}` / `\`case ${caseId.slice(0, 8)}\`` / `\`case ${caseId.slice(0, 10)}\`` — truncated raw backend UUID slices shown as the case reference in the dock header and case-created card | The hard rule explicitly lists "internal UUIDs" as forbidden. However, `caseId` is an *expression*, not a string literal — replacing it with something safe (a friendly sequential case label, or hiding it) requires new formatting logic, which is outside this wave's "string-literal only, no logic/prop/structural changes" mandate. Flagged for a future pass: give cases a physician-facing label distinct from the backend UUID (or hide the identifier from ordinary UI entirely and reserve it for a debug-flagged surface). |
| 8 | `web/components/copilot/CopilotDock.tsx` — `isFailedResult()` (`stringAt(root, "detail") ?? stringAt(root, "error") ?? "Action failed"`) rendered into `GenFailCard`'s `detail` prop for `create_case`/`extract`/`operate`/`simulate_recovery` failures | Passthrough of whatever `detail`/`error` string the backend action result contains, unsanitized | Checked `python/hearttwin/copilot.py` for what these four actions actually return on failure (without editing it — `python/` is out of my file-ownership lane): found no `"status": "failed"` dict pattern in `create_case`/`extract`/`operate`/`simulate_recovery` today (that pattern only appears in the separate `answer_case_question` path, for trace bookkeeping, not the user-visible result). So this passthrough does not appear to be actively triggered by a real leak today, but it is a live risk if a future backend change starts returning raw exception text in a `detail`/`error` field. Not fixed because (a) it isn't confirmed to be leaking today, and (b) a real fix means either a backend-side guarantee of clinical-safe failure text or replacing the passthrough with a static message — both beyond a literal-text swap. Flagged for the backend-facing half of this hardening effort. |
| 9 | `web/components/assistant/PhysicianBriefView.tsx`'s `EntryLine` (renders every key of `observed_evidence`/`derived_evidence`/`simulated_results`/etc. entries as `{key}: {value}`) and `ArtifactDetailPanel.tsx`'s provenance list (`ref.kind` / `ref.source_id` / `ref.description`) | Arbitrary backend dict keys and provenance `source_id` values rendered verbatim | This is by design per the file's own contract comment ("every section always renders... an explicit empty-state sentence... instead of hiding it" — Wave 3's honesty-over-polish rule for `DecisionSupportBundle`). Today's real `physician_brief.py` output uses clinical field names (checked: `observed_evidence`/etc. keys are cardiac-domain, not backend jargon), so no active leak was confirmed. But there is no allowlist/humanizer stopping a future backend field addition (e.g. a `tool_call_id` or `raw_provenance_ledger_id`) from being rendered verbatim. Not fixed — doing so safely needs a field-name allowlist/formatter (logic change), and confirming today's actual field names needed reading `physician_brief.py`, which is correctly Wave 3/Report-Personalization-Engineer territory, not a string-literal swap in this file. Flagged for the Report Personalization Engineer role in this same wave. |

### OUT-OF-SCOPE — real-looking leaks found elsewhere in `web/`, outside my 9-file mandate

These were found by the broader `web/`-wide grep (step 4 above) and are
**not** in the CopilotDock/CareGuardCopilot/assistant-7-files list this task
authorized me to edit. Listed here so a future pass has a starting point —
none of these files were touched.

| File | What was found | Note |
|---|---|---|
| `web/components/trace/AgentTraceTimeline.tsx` | A whole panel titled `"Agent trace"` (line 258), mounted unconditionally in `web/components/layout/AppShell.tsx:238` under `<ErrorBoundary name="Agent trace">` in "a right rail of compressed observability (agent trace, ...)" per that file's own contract comment — folds the live SSE trace into "per-agent spans," a `tool_call` event kind, etc. | This is the single largest concentration of literal "agent"/"tool_call" surface area in the whole frontend, and it is mounted in the ordinary product shell, not behind any visible dev-flag gate that I could confirm without reading `AppShell.tsx` in more depth (which I was told not to touch/audit this wave). **This is the highest-priority item for the next UI-cleanliness pass**: determine whether it's meant to be a judge/demo-facing "observability" feature (in which case it needs the same vocabulary pass as everything else — "Agent trace" → e.g. "Case timeline" / "Simulation activity") or a genuine dev-only panel that needs a `NEXT_PUBLIC_*_DEBUG` gate it currently lacks. |
| `web/components/careguard/runner/CareGuardRunner.tsx` | `"Run full agent analysis →"` button label (line 145), `"Agent run"` heading (line 188), `` `Agent run unavailable: ${e}` `` — a raw caught error interpolated directly into a log line shown to the user (line 98) | Same category as findings #2/#3 above (raw error interpolation) plus literal "agent" in button/heading text. Not touched — `CareGuardRunner.tsx` is not in my authorized file list. |
| `web/components/eval/EvalScorecard.tsx` | Contract comment references "the evaluator/critic agent's quality" — comment only, need to check the actual rendered labels in that component for "agent"/"critic" leakage | Not read in full this wave (out of scope); flagged for the same follow-up pass. |
| `web/components/intake/CaseIntakePanel.tsx:583` | `"intake agent gates input safety before extraction runs"` | Need to check if this is a code comment or rendered text — grep context suggests comment, but not verified in full; flagged. |
| `web/app/api/copilotkit/route.ts` | Literal `GET`/`POST` exports, `OpenAIAdapter`, `openai`/model env vars | This is the actual Next.js API route handler (server-side, not rendered UI) — almost certainly correctly out of the UI-cleanliness rule's scope (it's backend wiring, not a physician-facing surface), but flagged for confirmation since it wasn't in my mandate to make that call definitively. |
| `web/components/redis/RedisStatsRail.tsx` | Contract comment references the literal `/api/v1/redis-stats` endpoint | Comment vs. rendered text not fully verified; flagged. |

**Also explicitly out of scope per the task's own instruction (not investigated
at all this wave):** `web/components/twin/shadow-trial/`,
`web/components/twin/comparison/`, `web/components/twin/missing-piece/`,
`web/lib/twin/comparison/` — Codex's active, uncommitted work as of this
wave's `git status`. A future UI-cleanliness pass must audit these once they
stabilize; they are physician-facing (Shadow Trial UI, Split-Heart comparison,
Missing Piece UI) and therefore squarely within this spec's remit once they
land.

### LEFT ALONE — developer-only, correctly not touched

- `COPILOT_INSTRUCTIONS` in `CopilotDock.tsx` (lines ~257-283): a system
  prompt passed to `CopilotChat`'s `instructions` prop. This is sent to the
  LLM as orchestration context, never rendered in the chat transcript UI
  itself, so its references to `create_case`/`extract`/`operate`/action names
  and "multi-agent" are not a UI leak under this rule (they could still leak
  indirectly if the LLM parrots them back in a reply — noted as a residual
  behavioral risk, not a static string this audit can fix).
- All code comments referencing routes, waves, agents, payloads, etc. across
  the 9 in-scope files (e.g. `BeatITCopilotPanel.tsx:11`'s `POST
  /assistant/message` comment, `ArtifactCard.tsx`'s "Agent 16"/"Agent 18"
  attribution comments) — per the task's own instruction, comments and
  variable/type names are not UI leakage and were left untouched.
- `description` fields on `useCopilotAction` calls (e.g.
  `confirm_recovery_simulation`'s description) — these are tool-descriptions
  consumed by the CopilotKit runtime/LLM, not rendered chat text.

---

## Exact diffs made

### `web/components/careguard/CareGuardCopilot.tsx`
```diff
       const res = await careguardApi.copilot(caseId, query);
       setTurns((t) => [
         ...t,
-        { q: query, a: res.copilot.answer, via: res.copilot.used_anthropic ? "Claude" : "deterministic", grounded: res.copilot.grounded_on },
+        { q: query, a: res.copilot.answer, via: res.copilot.used_anthropic ? "AI-assisted" : "Case rules", grounded: res.copilot.grounded_on },
       ]);
       setQ("");
-    } catch (e) {
-      setTurns((t) => [...t, { q: query, a: `Error: ${(e as Error).message}`, via: "error", grounded: [] }]);
+    } catch {
+      setTurns((t) => [...t, { q: query, a: "Unable to complete this analysis right now. Please try again.", via: "error", grounded: [] }]);
     } finally {
```

### `web/components/assistant/BeatITCopilotPanel.tsx`
```diff
     } catch (cause) {
       const detail =
         cause instanceof AssistantApiError && cause.status === 404
           ? "The assistant is still warming up — this feature isn't connected yet."
-          : cause instanceof Error
-            ? cause.message
-            : "The assistant is unavailable right now.";
+          : "The assistant couldn't complete this request. Please try again.";
       setTurns((prev) => [...prev, { id: newId(), role: "notice", content: detail }]);
```

### `web/components/copilot/CopilotDock.tsx`
```diff
       <div className="flex items-center gap-1.5 text-[0.72rem] text-muted">
         <Pulse className="size-3.5 text-signal-dim" />
-        Streaming agent telemetry
+        Streaming simulation data
       </div>
```

### `web/components/assistant/ArtifactDetailPanel.tsx`
```diff
         <span>
-          A detailed view is not yet available for artifact type{" "}
-          <code className="ht-mono">{artifact.type}</code> — no backend generator produces a
-          typed payload for this type yet (Wave 4). Showing the raw payload data below instead
-          of a real view.
+          A formatted view is not yet available for this evidence type{" "}
+          <code className="ht-mono">{artifact.type}</code> — showing the available case data
+          below instead of a formatted view.
         </span>
```

---

## Verification

```
$ npx tsc --noEmit
(no output — clean)

$ npx eslint components/careguard/CareGuardCopilot.tsx components/assistant/BeatITCopilotPanel.tsx components/copilot/CopilotDock.tsx components/assistant/ArtifactDetailPanel.tsx
(no output — clean)

$ git status --short   # before and after edits
 M web/components/assistant/ArtifactDetailPanel.tsx
 M web/components/assistant/BeatITCopilotPanel.tsx
 M web/components/careguard/CareGuardCopilot.tsx
 M web/components/copilot/CopilotDock.tsx
(plus pre-existing Codex-owned modified/untracked files, all unrelated to this task and untouched by it)
```

No behavior, prop, or logic changes were made beyond the five string-literal
(or static-string-branch) swaps above; the only non-literal edits were
dropping the now-unused `cause instanceof Error` branch in
`BeatITCopilotPanel.tsx` and the now-unused catch binding `(e)` in
`CareGuardCopilot.tsx` — both are direct, mechanical consequences of removing
the leaked dynamic string, not independent logic changes.

---

## What remains for a future pass

1. **`web/components/trace/AgentTraceTimeline.tsx`** — the biggest open
   question. A panel literally titled "Agent trace," mounted unconditionally
   in the product shell (`AppShell.tsx`), showing per-agent spans and
   `tool_call` events. Needs a decision: keep as a judge-facing "meaningful
   orchestration" showcase (relabel per the vocabulary guide) or gate it
   behind an explicit debug flag per the hard rule. Not touched this wave —
   both the file and its mount site (`AppShell.tsx`) were off-limits.
2. **`web/components/careguard/runner/CareGuardRunner.tsx`** — literal
   "agent" in button/heading text plus a raw-error-interpolation pattern
   matching finding #2/#3 above. Not in my file mandate.
3. **Raw JSON dump in `ArtifactDetailPanel.tsx`'s `RawPayloadFallback`**
   (finding #6) — needs a real formatter/allowlist, not a text swap.
4. **Truncated case UUIDs shown as the case reference** in `CopilotDock.tsx`
   and `CareGuardCopilot.tsx` (finding #7) — needs a friendly case-label
   scheme, a logic change outside this wave's mandate.
5. **Unsanitized `detail`/`error` passthrough** from backend action results
   into `GenFailCard` in `CopilotDock.tsx` (finding #8) — not confirmed
   actively leaking today, but has no guardrail; worth a backend-side
   contract (always-clinical-safe failure text) as part of the
   Report-Personalization/Report-Consistency-Validator tracks of this same
   wave.
6. **Arbitrary backend dict keys rendered verbatim** in
   `PhysicianBriefView.tsx`'s evidence lists and `ArtifactDetailPanel.tsx`'s
   provenance list (finding #9) — needs a field-name allowlist/humanizer,
   best owned alongside the Report Personalization Engineer's work on
   `physician_brief.py`.
7. **Codex-owned UI** — `web/components/twin/shadow-trial/`,
   `web/components/twin/comparison/`, `web/components/twin/missing-piece/`,
   `web/lib/twin/comparison/` are physician-facing surfaces under active,
   uncommitted development and were correctly not audited or touched this
   wave (explicit instruction). They need their own UI-cleanliness pass once
   Codex's work stabilizes/commits.
8. **`EvalScorecard.tsx`, `CaseIntakePanel.tsx:583`, `RedisStatsRail.tsx`,
   `app/api/copilotkit/route.ts`** — flagged by the broad grep but not read
   in full or confirmed as genuine UI leaks (likely comments/server-side code
   in most cases); need a follow-up read-through to close out.
