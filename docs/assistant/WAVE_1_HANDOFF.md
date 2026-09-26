# Wave 1 Handoff — Discovery / Research

> Read `docs/assistant/GLOBAL_ARCHITECTURE.md` first — it is the standing
> contract for every wave, including this one's conclusions.

Wave 1 was pure research/audit. No code was touched. Five agents produced:
`CHAT_SURFACE_AUDIT.md`, `LAYA_RESEARCH.md`, `NVIDIA_MODEL_RESEARCH.md`,
`PHYSICIAN_WORKFLOWS.md`, `CURRENT_ARCHITECTURE.md`. This document
integrates their findings, resolves overlaps, and sets Wave 2's scope.

## Current problems (why this campaign exists)

- **Exactly TWO chat surfaces exist today, not one, not zero.**
  1. **"Cardiology Copilot"** (`web/components/copilot/CopilotDock.tsx`) —
     real CopilotKit/AG-UI, generative-UI cards, one human-in-the-loop step.
     Wired through `web/app/api/copilotkit/route.ts` →
     `add_fastapi_endpoint(app, sdk, "/copilotkit")` in
     `python/hearttwin/api.py:122` → 5 actions in `python/hearttwin/copilot.py`
     (`create_case`, `extract`, `operate`, `simulate_recovery`,
     `answer_case_question`). Only `answer_case_question` calls an LLM
     (OpenAI). Shown on the main console.
  2. **"CareGuard Copilot"** (`web/components/careguard/CareGuardCopilot.tsx`) —
     hand-rolled widget, plain `useState` (no persistence), plain REST
     (`POST /api/v1/careguard/cases/{id}/copilot` →
     `python/hearttwin/careguard/routes_analysis.py:50` →
     `careguard/copilot_agent.py`), backed by **Anthropic**, not CopilotKit.
     Flag-gated (`CAREGUARD_ENABLED`), shown on `/careguard*` routes and the
     CareGuard tab.
  - Both have **independent safety blocklists**
    (`copilot.py::_check_output_safety` / `_OUTPUT_RED_FLAGS` vs. CareGuard's
    own `_BLOCK` list + disclaimer string) — any merge must **union**, never
    drop, either.
  - `web/components/layout/AppShell.tsx:186-191` already hides the CopilotKit
    launcher on the CareGuard tab, with a comment admitting the collision
    ("to avoid two launchers"). This is the CSS-hiding anti-pattern
    AGENTS.md/campaign brief explicitly forbids as a "fix" — Wave 4 must
    replace it with a real merge.
  - No `/chat`, `/conversation`, `/assistant` REST routes exist. No
    server-side conversation-turn persistence exists anywhere (only
    case/artifact state persists). This is genuinely greenfield — nothing to
    migrate for conversation storage itself.

- **AGENTS.md is substantially stale** — treat `CURRENT_ARCHITECTURE.md` as
  authoritative for the items below; keep AGENTS.md §1 (safety, physics-core,
  test suite, secrets) as still binding regardless:
  - CopilotKit is **already fully wired** (route, SDK endpoint, 5 actions,
    generative-UI cards, human-in-the-loop) — this is a merge/extend target,
    not a greenfield build.
  - Deploy is actually **Vercel Python serverless** (`vercel.json`,
    `api/index.py`, `maxDuration: 60`) — no Dockerfile, no Hugging Face
    Spaces anywhere. Any new assistant backend work must respect the 60s
    serverless timeout and no-WebSocket assumption (existing trace stream
    already uses SSE for this reason — reuse that pattern for
    assistant streaming).
  - Redis is now **standard `redis.asyncio` over `REDIS_URL`**
    (`python/hearttwin/tools/redis_client.py`), not Upstash REST — the
    Upstash-specific limits in AGENTS.md (no `XREAD BLOCK`, 32KB fields,
    500K cmd/mo) no longer apply.
  - Weave is **still a stub** exactly as AGENTS.md warned: `_publish()` in
    `python/hearttwin/tools/weave_trace.py:174-175` calls a
    nonexistent-in-practice `client.publish()`, no `@weave.op` decorators
    exist, no `client.flush()`, `get_run_url()` fabricates a URL. Out of
    scope for this campaign but do not claim Weave tracing works.

- **Physiology/evidence logic is richer than the campaign brief assumed, but
  entirely unreachable by any assistant today:**
  - Real, deterministic, UI-wired: causal/scenario engine (`web/lib/twin/scenario/*.ts`),
    plausible-twin ensembles (`python/hearttwin/ensemble.py`, `/api/v1/twin/ensemble/{id}`,
    `/distributions`, with a real `assumptions: list[str]` field), component
    report builder (`web/lib/heart/patient/adapter.ts`), evidence grouping
    (`web/lib/heart/evidence/index.ts`), provenance lineage
    (`web/lib/twin/provenance/index.ts`), browser-local timeline
    (`web/lib/twin/snapshots/`), AHA 17-segment/coronary mapping
    (`python/hearttwin/tools/cardiac_findings.py`).
  - **"Shadow Trials," "Split Heart," "Missing Piece" are 100% unbuilt** —
    only plan docs exist, zero matching code. **Live update:** `git status`
    during Wave 1 integration shows Codex (the other agent sharing this
    working tree, coordinating via hacp — see below) is actively adding
    `python/hearttwin/shadow_trial_contracts.py`,
    `shadow_trial_identity.py`, `shadow_trial_metrics.py`,
    `storage/shadow_trial_store.py` right now. **Do not build a
    `run_shadow_trial`/`get_shadow_trial` tool against this until Codex's
    work lands and is verified** — treat it as a Wave-3-or-later dependency,
    not something to assume exists.
  - `answer_case_question`'s deterministic fallback only echoes 5 flat
    summary metrics — it cannot cite evidence, segments, assumptions, or
    scenario deltas. **Wave 3's job is mostly "expose real existing
    frontend/ensemble logic through tools," not "invent new physiology."**
  - No sensitivity/dominance-analysis code exists ("which assumptions
    dominate," "what evidence would most constrain this" are true gaps
    needing new logic).
  - **Provenance is fragmented across 4 non-interoperable vocabularies**:
    backend `ValueSource` (4 kinds), frontend `EvidenceKind` (6 kinds),
    timeline `TwinEventSource` (7 kinds), causal `CausalSourceKind` (6
    kinds). Wave 2's conversation/artifact schema work must pick one
    canonical vocabulary or an explicit mapping — do not invent a 5th.
  - Safety guardrails are real and load-bearing:
    `python/hearttwin/agents/intake_agent.py` regex-classifies and blocks
    emergency/treatment/diagnosis intent (`_classify_intent_with_rules`,
    `_merge_decisions` — an LLM can never soften a rule-based block), plus
    `copilot.py:418 _check_output_safety` on every answer. **Do not weaken
    or bypass either when building the unified tool registry.**

## Chosen Laya integration hypothesis (confirmed, not just hypothesized)

- Real project, Apache-2.0, non-autoregressive encoder (ModernBERT-large
  421M / mmBERT-base 322M) with typed `choice`/`score`/`noul` decision heads,
  trained via RLCD, an auto-routing `Router`, real Docker compose (CPU/GPU/
  HTTP/Spark), real HTTP server (`laya-serve`, `POST /v1/systemone`,
  Jev-wire-compatible), and a real (if unverified-in-depth)
  `laya/integrations/langchain.py`.
- **Author-attribution correction applied**: the earlier claim ("Ananda
  Kishore, mathematician") is **refuted** — verified creator is Nandakishor
  Mukkunnoth (Convai Innovations). Never repeat the old claim.
- **Jev terminology correction applied**: Jev is TypeSafe AI's closed,
  commercial-only API — never say "self-hosted Jev." Use "Laya-based
  System-1 decision layer" or "Jev-compatible" only where the wire-protocol
  compatibility is meant literally.
- Real benchmark numbers exist (fine-tuned: 0.766 acc / 0.061 Brier / 0.213
  ECE vs. base ~0.35 acc zero-shot; stated Jev baseline 0.727 acc / 0.144
  ECE) — note Laya's fine-tuned checkpoint has **worse calibration (ECE)**
  than the Jev baseline despite better accuracy. **Do not treat Laya
  probabilities as calibrated confidence until BeatIT's own calibration
  campaign (Wave 5) runs.**
- Confirmed integration boundary (matches `GLOBAL_ARCHITECTURE.md`): Laya
  may only do non-clinical routing/gating decisions; must never touch
  diagnosis/treatment/emergency-triage.

## NVIDIA candidate shortlist (confirmed model IDs, not final selection)

- **Fast**: `nvidia/nemotron-3.5-lightning-30b-a3b` — 30B total/3B active
  hybrid Mamba-2+MoE, up to 1M context, branded for long-running agents.
- **Deep**: `nvidia/nemotron-3-super-120b-a12b` — 120B total/12B active, 1M
  context native but NVIDIA docs note 262,144 as the practical default
  (Nemotron 3 Ultra 550B/55B active exists as an untested heavier option).
- **Safety**: **revise the original hypothesis** — current model is
  "Nemotron 3.5 Content Safety" (Gemma-3-4B-based, 23 categories, 12
  trained + ~140 zero-shot languages, multimodal, optional THINK-mode), not
  the older 8B NemoGuard (Llama-3.1-based) — though the older NemoGuard is
  still live and is what NVIDIA's own Ambient Healthcare Agents blueprint
  actually uses today. Evaluate both in Wave 6.
- API pattern (needs re-verification once real keys exist, per researcher's
  own flag): OpenAI-compatible REST at `https://integrate.api.nvidia.com/v1`,
  `Authorization: Bearer nvapi-...`. Rate-limit/pricing figures found so far
  are third-party-reported, not NVIDIA's own documented SLA — verify live in
  Wave 2/6 once keys are available.
- Ambient Healthcare Agents reference pattern: audience-split agents
  (provider vs. patient), heavier model for high-stakes notes + lighter
  model for high-volume interaction (direct precedent for our fast/deep
  split), safety as an **independent two-model guardrail tier** wrapping
  reasoning models, every tier as a swappable NIM microservice. Reference
  only — do not copy wholesale.

## Physician workflows mapped

See `PHYSICIAN_WORKFLOWS.md`'s "Canonical Tool Candidates" — ~8 concrete,
real-backed candidates (`get_component_report`, `get_component_evidence`,
`get_provenance`, `get_cardiac_findings`, `run_scenario_experiment`,
`get_scenario_pv_loop`, `get_ensemble`/`get_ensemble_distributions`,
`get_ensemble_assumptions`, `get_timeline`) plus an explicit **do-not-build-
yet list** (shadow trial, split heart, missing piece, dominant-assumptions,
constraining-evidence — need new logic before any tool wrapper is useful).

## Architecture constraints for Wave 2 (binding)

1. Merge target is CopilotDock + CareGuardCopilot into one conversation
   engine — not a fresh build. Union both safety blocklists.
2. Assistant backend must work within Vercel's 60s serverless function
   limit; use SSE (existing trace-stream pattern), not WebSockets or
   long-lived connections.
3. Redis integration point is standard `redis.asyncio`/`REDIS_URL` — ignore
   AGENTS.md's Upstash-specific guidance.
4. Pick one canonical provenance vocabulary (or an explicit mapping) across
   the 4 existing ones before designing the artifact/context schema.
5. Do not build tools for Shadow Trial / Split Heart / Missing Piece yet —
   watch for Codex's shadow_trial_* work landing, verify it, then revisit.
6. Preserve `intake_agent.py`'s rule-based blocking and both existing output
   safety checks; the new unified safety layer must be their superset, never
   their replacement-with-gaps.
7. Do not lock a final NVIDIA model or Laya threshold yet — Wave 2 builds
   the adapter/pool skeletons with deterministic fallback; benchmarking is
   Wave 6 (Laya calibration is Wave 5).

## Files likely to change in Wave 2

- New: unified conversation API/router (Python, under `python/hearttwin/`),
  Laya adapter module, NVIDIA key-pool module, canonical tool registry
  module, safety/numeric-validation module.
- Modified: `python/hearttwin/api.py` (mount new conversation route),
  possibly `python/hearttwin/copilot.py` and
  `python/hearttwin/careguard/copilot_agent.py` (only to the extent needed
  to route through the new registry — full UI consolidation is Wave 4).
- Not touched: `python/hearttwin/tools/cardiac_state.py`,
  `hemodynamics.py`, `recovery_sim.py` (physics core, sacred per AGENTS.md
  §1.3), anything under `python/hearttwin/shadow_trial_*` (Codex's lane).

## Coordination note (hacp)

Working tree is shared live with Codex (confirmed by the user: "codex
sessions are live"). hacp session `s-907350372a414fbda3edcba106c3828f`
started as peer a, claiming exactly the `docs/assistant/*.md` files Wave 1
produced. Codex has not joined as peer b yet (session still "opening") but
is already visibly active in the tree (Shadow Trial files, `Progress.md`,
`docs/hackathon/M5_5_*`, `docs/credibility/beatit-model-manifest.json`).
None of that overlaps Wave 1's or (per the constraints above) Wave 2's
planned files. Wave 2 agents must re-run `hacp --peer a poll` before
proposing any contract for files outside `docs/assistant/` and must scope
`git add` to only their own deliverables — never `git add -A` — given the
shared, uncommitted working tree.

## Global Architecture Compliance: YES

No competing router/context/registry/safety-layer/conversation-store was
created in Wave 1 (research only). Wave 2 must re-affirm this at its own
handoff.
