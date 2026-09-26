# Wave 5 Handoff — Laya Decision Specialization (INCOMPLETE)

> Read `GLOBAL_ARCHITECTURE.md` and Waves 1-4 handoffs first.

**This wave is incomplete and should not be treated as a normal wave
close-out.** 3 of 5 sub-agents failed outright partway through their work
when this account hit its monthly spend limit (rate-limited, HTTP 429,
resets 2pm UTC). The lead did not spawn replacement agents, since any
retry before the reset would fail identically. Per the campaign's own
"Do NOT write 'Laya calibrated' unless measured" rule, this handoff makes
no claim beyond what actually landed.

## What actually completed

- **Agent 23 (Laya Specialization Engineer)** — `docs/assistant/wave5/laya-specialization.md`.
  Delivered a full report before the rate limit hit its own follow-up
  background work. Conditional decision framework (no fine-tuning
  justified for any of the 7 decision types, independent of accuracy —
  Laya isn't reachable from this environment and there's nowhere near
  enough labeled data). Explicitly, honestly built without Agent 22's
  numbers, which never arrived (polled and confirmed absent, twice).
- **Agent 24 (Decision Policy Engineer)** — `python/hearttwin/assistant/laya_policy.py`,
  `test_laya_policy.py` (45 tests), `docs/assistant/wave5/decision-policy.md`.
  Fully-parameterized threshold policy, every value honestly marked
  "provisional-default" (0.70 uniform floor, not 7 fabricated distinct
  numbers). Structural clinical-authority guard verified live (raises
  `ClinicalAuthorityRefused` on 8 misuse variants, zero false positives on
  the 7 real decision types). Confirmed `orchestrator.py` currently only
  calls 2 of the 7 decision types (`classify_intent`, `select_tool_family`)
  — the other 5 policy entries exist but have no live call site yet.

## What did NOT complete

- **Agent 21 (Decision Fixture Engineer)** — FAILED before writing the
  actual fixture data file. Only an empty `python/hearttwin/tests/fixtures/__init__.py`
  package marker exists on disk (uncommitted, harmless, left in place for
  whoever resumes this). **No labeled BeatIT-specific decision fixtures
  exist anywhere in this repo as of this handoff.**
- **Agent 22 (Laya Evaluation Engineer)** — FAILED before completing either
  the real-Laya-Docker attempt or the fallback-only evaluation. No
  `docs/assistant/wave5/laya-evaluation.md` exists. **No real accuracy,
  confusion-matrix, Brier, or ECE numbers exist for either the deterministic
  fallback or a real Laya instance.** This is the single biggest gap: every
  other Wave 5 deliverable (the policy thresholds, the specialization
  verdict) is explicitly conditional on this evaluation existing, and it
  doesn't.
- **Agent 25 (Decision Adversary)** — FAILED before completing its attack
  suite (had started an exploratory scratch script per its last visible
  action). **No adversarial/red-team findings exist against the real
  orchestrator/safety_validator/laya_adapter pipeline from this wave.**
  Wave 3's own clinical-language audit already found and fixed one real
  issue ("can I take"), but that was incidental to a different task, not a
  systematic adversarial pass — this remains a real, unclosed gap.

## Docker/infrastructure state

Agent 22 was mid-attempt at standing up a real Laya instance via Docker
when it was cut off. Check for any leftover container before resuming:

```
docker ps -a | grep -i laya
```

If one exists, it may be an orphaned attempt from this wave — inspect
before removing (it could contain partial progress worth reusing, e.g. an
already-pulled image or a running server that just needs a fixture set
pointed at it).

## Global Architecture Compliance: N/A — wave incomplete

The compliance question doesn't meaningfully apply to an interrupted wave.
No second router/context/registry/safety-layer was created by what did
land (`laya_policy.py` is additive and inert — nothing calls
`should_defer_to_clarification` yet).

## Required before Wave 5 can be considered actually done

1. Re-run Agent 21's task (decision fixtures) once quota resets — nothing
   else in this wave is trustworthy without it.
2. Re-run Agent 22's task (real evaluation) — check for and reuse/clean up
   any orphaned Docker container first.
3. Once real numbers exist, revisit `laya_policy.py`'s thresholds (use its
   own `DecisionAccuracy.with_measured_accuracy` API — no code change
   needed, just supply real numbers) and re-resolve Agent 23's conditional
   fine-tune-or-not table against them (the "no fine-tuning justified"
   conclusion should hold regardless, per its own infra-scarcity reasoning,
   but the fallback-vs-defer verdicts per decision type were left
   conditional and need real data to resolve).
4. Re-run Agent 25's task (adversarial red-team) — this is a real, open
   safety-relevant gap, not just an incompleteness formality.

## Recommendation

**Do not proceed to Wave 6 (NVIDIA benchmarking) until Wave 5 is actually
completed**, or at minimum until the rate limit resets and a conscious
decision is made about whether to backfill Wave 5 first or proceed with
Wave 6 in parallel (Wave 6 doesn't technically depend on Wave 5's outputs —
they're different subsystems — but running two waves this size back-to-back
through the same quota constraint risks the same interruption). Surfacing
this choice rather than deciding it unilaterally.
