# Wave 3 Handoff — Physician Intelligence

> Read `docs/assistant/GLOBAL_ARCHITECTURE.md`, `WAVE_1_HANDOFF.md`, and
> `WAVE_2_HANDOFF.md` first. Wave 4 agents must also read this file.

Wave 3 wired Wave 2's isolated pieces into a real, working (if still
LLM-free) pipeline, and added physician-facing intelligence on top. All work
stayed inside `python/hearttwin/assistant/`, `python/hearttwin/tests/`, and
`docs/assistant/wave3/` except two files Agent 11 was explicitly permitted
to modify (`router.py`, its own Wave 2 predecessor) and two small
integration fixes the lead applied directly after all 5 agents reported
(see "Integration fixes" below). Committed at `09d9abc`. Full suite:
**988 passed, 1 skipped**, no regressions.

## What was implemented

1. **Orchestrator + context resolution** (`context_resolver.py`,
   `orchestrator.py`, Agent 11) — `router.py`'s `POST /message` now calls a
   real pipeline instead of Wave 2's stub: safety classification first
   (unconditional, before Laya or context ever run — a bypass is
   structurally impossible, not just unlikely) → context/clarification
   check → Laya intent + tool-family routing → tool dispatch via the real
   registry (generic arg-matching against `ConversationContext`, not
   per-tool special-casing) → output safety + numeric-claim validation on
   any tool-grounded text → disclaimer always attached. No LLM call exists
   anywhere in this path — every non-blocked, non-clarification response is
   either a real tool result or an honest `UNSUPPORTED`/`INSUFFICIENT_EVIDENCE`,
   never fabricated prose. `apply_context_event` covers all 5 UI event
   types from `GLOBAL_ARCHITECTURE.md` as a pure, frontend-callable
   transform (frontend itself not built — Wave 4's job).
2. **Provenance mapping** (`provenance_mapping.py`, Agent 13) — of the 4
   legacy vocabularies named in Wave 1, only **`ValueSource` is real
   Python-side data**; `EvidenceKind`, `TwinEventSource`, and
   `CausalSourceKind` are confirmed TypeScript-only and were **not** faked.
   A second real vocabulary not on the original list,
   `EnsembleProvenance.origin_quality`, was found and mapped too. Both
   mappings are exhaustive and raise on unknown input rather than silently
   defaulting. `get_provenance_for_ensemble` / `get_provenance_for_cardiac_findings`
   are plain importable functions, not yet wired into the tool registry or
   the orchestrator's output — that wiring is explicitly available now for
   Wave 4 to pick up (Agent 14's brief generator already has an
   `extra_provenance` parameter built for exactly this).
3. **Physician brief** (`physician_brief.py`, Agent 14) — generates a
   `PHYSICIAN_BRIEF`-typed `AssistantArtifact` with a `DecisionSupportBundle`
   payload (no `recommended_treatment` field or synonym, structurally
   verified by test). Key judgment call, carefully reasoned: **all**
   `get_cardiac_findings` output is `derived_evidence`, `observed_evidence`
   is `[]` — because nothing the 4 T0 tools expose is genuinely raw/observed
   (everything is either a threshold classification, a lookup-table label,
   or a simulation output already run through the deterministic pipeline).
   The one place real observed data lives (`CardiacTwinState.source_map`,
   `ValueSource.FILE_EXTRACTION`/`USER_INPUT`) isn't exposed by any tool yet
   — Wave 4/later can close this by wiring `get_raw_provenance_ledger`
   (built this wave, see below) into the brief. `missing_evidence`,
   `conflicts`, `possible_interpretations` are `[]` because no detection
   logic exists (confirmed gap, not a bug) — `limitations[]` says so
   explicitly and specifically for each gap.
4. **Tool registry expansion** (`physician_tools.py`, Agent 12) — 4 new
   real T0 tools, none faked: `get_pv_loop` (baseline PV loop, already
   computed on every `/operate` call, simply never wrapped before),
   `get_raw_provenance_ledger` (exposes `CardiacTwinState.source_map`
   honestly as unbound/raw, not component-scoped), `get_findings_by_region`
   (filters `get_cardiac_findings`'s real output, no new logic),
   `get_ensemble_summary` (composite of the 3 existing ensemble tools).
   Component report, evidence-by-component, and timeline are re-confirmed
   frontend-only — still correctly not built.
5. **Clinical-language integrity guard** (`language_integrity.py`,
   Agent 15) — audited every judgment call Wave 2's safety validator made;
   verdicts: 4 of 5 KEEP AS-IS, 1 NEEDS-NARROWING (see below, fixed).
   Built `scan_for_prescriptive_language` + `scan_assistant_module_for_violations`
   as a reusable static guard for future waves. **Real scan of the actual
   codebase found 0 violations** — reported honestly, not tuned to that
   result.

## Integration fixes applied by the lead after all 5 agents reported

Two real bugs surfaced during the wave, both in Wave 2's own
already-committed files (not shared/live-app files), both small and
well-tested — fixed directly rather than spawning another agent, per the
campaign's "solve ordinary engineering blockers and continue" rule:

1. **`laya_adapter.py` fallback tool-family bucket ordering** (found by
   Agent 11): the keyword `"ensemble"` was checked under the `EXPERIMENT`
   bucket *before* `UNCERTAINTY`, so any message mentioning "ensemble"
   misrouted to a category with no tools, instead of `UNCERTAINTY` where
   `get_ensemble`/`get_ensemble_distributions`/`get_ensemble_assumptions`/
   `get_ensemble_summary` actually live. Moved `"ensemble"` to the
   `UNCERTAINTY` pattern list. No existing test depended on the old
   (wrong) behavior; verified via full suite re-run.
2. **`safety_validator.py`'s bare `"can i take"` pattern** (found and fixed
   by Agent 15 in its own new file, folded into `safety_validator.py` by
   the lead): the pattern collided with BeatIT's own vocabulary ("can I
   take this simulation further?", "can I take a closer look at the PV
   loop?"). Removed the bare pattern; wired in Agent 15's
   `narrow_can_i_take_check` (flags only when a medication/dose-adjacent
   word appears within an 8-word window) via a new import in
   `safety_validator.py`. No circular import (`language_integrity.py` has
   no dependency back on `safety_validator.py`). Verified via the full
   combined assistant test suite (152 tests) plus full repo suite (988
   passed) after the change.

Both fixes are minimal, additive to what the relevant Wave 3 agent already
built and tested, and did not require touching any file outside the
`assistant/` package.

## Shared contracts changed

None outside `assistant/` itself. Within it: `router.py` (Wave 2) now calls
real logic instead of a stub (expected, planned evolution, not a "shared
contract" in the cross-team sense); `laya_adapter.py` and
`safety_validator.py` (both Wave 2) received the two integration-fix edits
above — their public APIs (method names, signatures, return types) are
unchanged, only internal keyword-matching logic was corrected.

## Files added

`python/hearttwin/assistant/{context_resolver,orchestrator,provenance_mapping,physician_brief,physician_tools,language_integrity}.py`,
matching test files, `docs/assistant/wave3/{context-and-orchestration,provenance-mapping,physician-brief,physician-tooling,clinical-language-integrity}.md`.

## Files modified

`python/hearttwin/assistant/router.py` (Agent 11, planned), `laya_adapter.py`
and `safety_validator.py` (lead, the two integration fixes above). Nothing
outside `python/hearttwin/assistant/`.

## Architecture decisions

- Safety-first ordering in the orchestrator (safety classification runs
  before context resolution and before any Laya call) is now the settled
  pipeline shape — Wave 4+ should treat this ordering as load-bearing, not
  incidental.
- `ConversationContext` has no `case_id` field (only `patient_id`), so
  `get_cardiac_findings` (which needs `case_id`) is currently unreachable
  through the generic orchestrator dispatch — only the 3 ensemble-family
  tools are reachable via `context.ensemble_id` today. This is a real,
  documented gap (Agent 11), not silently papered over. **Wave 4 or later
  needs to decide**: add `case_id` to `ConversationContext`, or establish
  that `patient_id`/`case_id` are meant to be the same identifier and unify
  them — this is a judgment call for whoever does the next context-schema
  change, not something this handoff resolves.
- Provenance coverage is honestly partial (1.5 of 4 legacy vocabularies).
  The remaining 3 are TypeScript-only; closing that gap requires either a
  frontend-side mirror of the canonical mapping, or the frontend sending an
  already-canonical provenance tag when it calls the future assistant API.
  This is now an explicit **Wave 4 (UI) dependency**.

## A safety-validator false positive found and locally handled (needs Wave 4 review)

Agent 14 found that `ensemble.py`'s own hardcoded protective disclaimer
text (present on every ensemble ever produced — "...are not clinical
confidence intervals.") trips `safety_validator.check_output_safety`'s
`_BLOCKED_PATTERNS` bare `\bclinical(ly)?\b` rule, which has no allowlist
entry for it (unlike `safety.py`'s own `DISCLAIMER`, which is allowlisted
for similar wording). This is a **systemic** false-positive class, not a
one-off — the same pattern independently hits `cardiac_findings.py`'s
disclaimer on the word "diagnosis" too. Agent 14 did not touch
`safety_validator.py` (out of scope) and instead handled it narrowly inside
`physician_brief.py`'s own bundle-scan logic: a block is only tolerated
when it is *exactly* that one documented, verified-safe pattern; any other
match anywhere still hard-fails immediately, unchanged. **This needs human
or Wave 4 review** — the right long-term fix is probably an allowlist entry
in `safety_validator.py` itself (mirroring how `safety.py`'s `DISCLAIMER`
is already allowlisted), not a per-caller workaround, but that's a
`safety_validator.py` change and deserves its own deliberate review rather
than a rushed fix during this handoff.

## Tests

152 tests across all Wave 2+3 assistant modules combined, all passing
together. Full repo suite: 988 passed, 1 skipped — up from Wave 2's 899,
consistent with Wave 3's additions, zero regressions at any point,
including through the two integration fixes.

## Known failures

None. Known **gaps** (not failures, all documented above or in individual
wave3/*.md design notes): `case_id`/`patient_id` schema mismatch limiting
orchestrator tool reachability; provenance mapping covers 1.5/4 legacy
vocabularies; the "clinical" word false-positive needs a proper
`safety_validator.py`-level fix; `observed_evidence` is always empty until
a tool exposes genuinely-observed (not derived) data.

## Security / medical risks

- No new risk surface — nothing from Wave 3 is mounted into the live app
  (`router.py` still isn't included in `api.py`).
- The safety-validator false positive above is currently handled safely
  (fails closed, not open) but should not be considered fully resolved
  until it gets a proper fix in `safety_validator.py` itself.
- `DecisionSupportBundle` has no `recommended_treatment` field, verified
  structurally by test — this remains true after Wave 3.

## Next-wave dependencies (Wave 4 — One Chat UI)

1. Mount `router.py` into `python/hearttwin/api.py` (still just the one
   documented line — `api.py` is Codex's active file, re-check `git status`
   immediately before this specific edit, don't assume it's still in the
   state this handoff describes).
2. Build the frontend caller for `apply_context_event` (shape documented in
   `docs/assistant/wave3/context-and-orchestration.md`).
3. Wire `provenance_mapping.py`'s functions into `physician_brief.py`'s
   `extra_provenance` parameter and/or directly into tool results — both
   pieces exist now, just not connected.
4. Decide the `case_id`/`patient_id` schema question above before physician
   conversations can reach `get_cardiac_findings`/`get_pv_loop`/
   `get_raw_provenance_ledger`/`get_findings_by_region` through the
   orchestrator.
5. Get a proper review + fix for the `safety_validator.py` "clinical" word
   false positive (see above) — don't let it linger as a per-caller
   workaround into later waves.
6. Consolidate `CopilotDock` and `CareGuardCopilot` (Wave 1's core finding)
   onto this pipeline — this is the actual "one chatbot" merge and hasn't
   started yet; Waves 2-3 built the new engine but the two legacy UI
   surfaces are untouched.
7. Codex has still not joined the hacp session as peer b through 3 full
   waves despite continuous activity in the shared tree — Wave 4 should not
   assume this changes; keep checking `git status` before every edit to a
   file outside `python/hearttwin/assistant/`/`tests/`/`docs/assistant/`.

## Global Architecture Compliance: YES

No second router/context/tool-registry/safety-layer/conversation-store was
created. The orchestrator is the single pipeline; Laya's boundary (7 bounded
decisions only) is unchanged and still structurally enforced; no
`recommended_treatment` field exists anywhere; the canonical provenance
enum was extended in coverage, not duplicated. Two real bugs found during
the wave were fixed at the source rather than worked around in multiple
places.
