# AGENTS.md — BeatIT operating rules

> Read this before working in the repository. The actionable backlog is
> [`docs/TASKS.md`](./docs/TASKS.md); product context is in
> [`docs/PLANNING.md`](./docs/PLANNING.md).

## Mission and product position

> **BeatIT helps cardiologists explain and explore bounded recovery scenarios
> using patient data and deterministic cardiovascular modeling—without allowing
> an LLM to invent clinical calculations.**

The primary user is a cardiologist preparing for or conducting a supervised
recovery/follow-up conversation. Recovery planning is difficult to personalize
and explain when patient evidence, physiological models, and care-team reasoning
remain disconnected.

BeatIT is an educational and research simulation, not a medical device. Do not
claim diagnosis, treatment selection, outcome prediction, clinical validation,
or suitability for unsupervised patient use.

Weave, Redis, CopilotKit, multi-agent orchestration, and other providers are
implementation choices. Preserve useful integrations, but never prioritize or
present them ahead of workflow value, scientific credibility, safety, and demo
reliability.

## Golden rules

1. **Protect the clinical workflow.** The reliable path is: select/create case →
   enter evidence → build baseline → ask a relevant question → run one bounded
   scenario → compare → explain assumptions and limitations → summarize/export.
2. **Keep numerical authority deterministic.** LLMs may extract, orchestrate, and
   explain. They never calculate physiology or silently alter model results.
3. **Show epistemic status.** Distinguish measured, extracted, inferred,
   prior-filled, derived, and simulated values. Preserve source provenance,
   supported confidence, assumptions, and limitations.
4. **Keep safety boundaries persistent.** Block diagnosis, treatment, prescribing,
   and emergency guidance. Keep the canonical disclaimer on all required success
   and error surfaces. A disclaimer does not replace specific boundaries.
5. **Do not overclaim.** Say “bounded simulated trajectory,” not forecast or
   predicted outcome. Say “computational credibility evidence,” not clinical
   validation.
6. **Verify before marking done.** Run each task's Verify gate and record results.
   New behavior requires focused tests.
7. **Protect sensitive data.** Commit no secrets or identifiable patient data.
   Do not log raw uploads. Demo with synthetic, de-identified, or appropriately
   licensed public evidence and label its origin.
8. **Preserve the current UI unless a task explicitly authorizes UI changes.**

## Coordination

- Claim work in `docs/TASKS.md` as `WIP @handle`; mark it `DONE` only after its
  Verify gate passes, or `BLOCKED` with a concise reason.
- Respect task file ownership and existing uncommitted work.
- Backend work lives under `python/` and `api/`; frontend work lives under `web/`.
- Keep `web/types/*` aligned with backend contracts.
- Historical sponsor documents may remain as archive material, but
  `AGENTS.md`, `docs/TASKS.md`, and `docs/PLANNING.md` are authoritative.

## Engineering constraints

- Preserve backward compatibility unless a task explicitly permits a break.
- The formulas in `python/hearttwin/tools/cardiac_state.py`,
  `hemodynamics.py`, and `recovery_sim.py` require explicit review and new golden
  evidence before modification.
- Prefer standard-library and existing project solutions over new dependencies.
- Keep loading, empty, missing-data, provider-failure, and safety-block behavior
  explicit.
- Optional providers must degrade honestly. Never replace unavailable output
  with invented data.
- Do not commit `.env`, secrets, `node_modules`, generated build output, local
  databases, raw patient data, or unlicensed assets.

## Validation standard

At minimum, release evidence must include:

- a deterministic golden case with expected-versus-produced outputs;
- repeated runs producing identical baseline output for identical inputs;
- bounded-scenario tests, including invalid and boundary inputs;
- provenance and measured/inferred/simulated classification checks;
- safety red-team cases for diagnosis, treatment, and emergency requests;
- documented model assumptions and limitations;
- a deployed end-to-end smoke test plus a local fallback rehearsal.

Clinician feedback is valuable when available, but must be described as
preliminary feedback—not clinical validation.

## Product and trust boundaries

**Intended use:** clinician-supervised education and communication using
inspectable cardiovascular simulations.

**Unsupported use:** diagnosis, treatment or medication selection, emergency
triage, autonomous care decisions, or validated patient-outcome prediction.

Every result should make it possible to answer:

- Which values came from supplied evidence?
- Which values were derived, inferred, or filled from priors?
- Which values are hypothetical simulation outputs?
- What assumptions and bounds produced the scenario?
- What is missing or uncertain?
- Can the result be reproduced?

## Run and verify

```bash
pnpm test:py
pnpm check
uvicorn api.index:app --reload --port 8000
curl localhost:8000/api/v1/system-check
cd web && pnpm dev
```

Use the repository's current test count rather than hard-coding it in docs.
`GET /api/v1/system-check` is the fastest deterministic backend smoke test.

## Definition of done

- One clinically credible workflow works end to end locally and on the public
  demo.
- The baseline and scenario are deterministic and reproducible.
- Comparison views expose assumptions, provenance, uncertainty/limitations, and
  value status without implying clinical prediction.
- Missing-data, loading, failure, and safety-block paths behave honestly.
- Golden, repeatability, safety, and contract tests pass.
- The pitch identifies the user, painful workflow, impact, buyer, adoption path,
  privacy boundary, and realistic regulatory posture.
- A backup recording or screenshots can carry the demo through provider or
  network failure.

## Git discipline

- Never push to the default branch without explicit permission.
- Keep commits small and descriptive; include task IDs and Verify output in PRs.
- Push transient failures may be retried up to four times with exponential
  backoff.
