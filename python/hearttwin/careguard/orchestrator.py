"""CareGuard staged orchestrator — Vercel-safe, one bounded stage per call.

POST /runs           → create_run (stage 1 pending)
POST /runs/{id}/next → advance_run: execute EXACTLY ONE stage (locked, idempotent)
GET  /runs/{id}      → get_run

Each stage rebuilds its context from persisted case + accumulated prior outputs
(stateless between serverless requests), runs its agent, persists the result, and
appends an audit event. Failures retry once; a failed stage is never silently
skipped, and a fallback is never reported as clean success.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from python.hearttwin.careguard import audit
from python.hearttwin.careguard.agents import (
    care_plan_composer_agent,
    clinical_critic_agent,
    encounter_intake_agent,
    fhir_context_agent,
    guideline_evidence_agent,
    hearttwin_scenario_agent,
    medication_safety_agent,
    multimorbidity_agent,
)
from python.hearttwin.careguard.constants import DISCLAIMER, STAGE_CLINICIAN_REVIEW_READY, STAGE_ORDER
from python.hearttwin.careguard.errors import RunNotFoundError, StageExecutionError
from python.hearttwin.careguard.memory import keys, redis_store
from python.hearttwin.careguard.schemas import (
    CareGuardCase,
    CareGuardContext,
    CareGuardRun,
    CareGuardStageResult,
    ClinicalFact,
)

_AGENTS = {
    "encounter_intake": encounter_intake_agent.run,
    "fhir_context": fhir_context_agent.run,
    "multimorbidity_analysis": multimorbidity_agent.run,
    "guideline_evidence": guideline_evidence_agent.run,
    "medication_safety": medication_safety_agent.run,
    "candidate_composition": care_plan_composer_agent.run,
    "hearttwin_scenarios": hearttwin_scenario_agent.run,
    "clinical_critic": clinical_critic_agent.run,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_stage(completed: list[str]) -> str | None:
    for s in STAGE_ORDER:
        if s not in completed:
            return s
    return None


async def create_run(*, case_id: str, workflow_intent: str, clinical_question: str) -> CareGuardRun:
    record = await redis_store.get_json(keys.case_record(case_id))
    if not record:
        raise RunNotFoundError(f"No CareGuard case {case_id!r} — import a FHIR bundle first")

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    run = CareGuardRun(
        run_id=run_id,
        case_id=case_id,
        status="created",
        workflow_intent=workflow_intent,
        current_stage="",
        next_stage=STAGE_ORDER[0],
        created_at=_now(),
        updated_at=_now(),
        persisted=redis_store.redis_configured(),
        disclaimer=DISCLAIMER,
    )
    await _save_run(run, prior_outputs={"bundle_id": record.get("source_bundle_id"),
                                        "clinical_question": clinical_question})
    await redis_store.set_json(keys.case_latest_run(case_id), {"run_id": run_id})
    await audit.record(case_id=case_id, run_id=run_id, actor="careguard_orchestrator",
                       action="created run", detail={"workflow_intent": workflow_intent})
    return run


async def _persist_case_artifacts(case_id: str, prior: dict[str, Any]) -> None:
    """Mirror the merged stage artifacts under case-scoped keys for the getters."""
    mapping = {
        keys.case_context(case_id): prior.get("patient_context"),
        keys.case_multimorbidity(case_id): prior.get("cross_organ_matrix"),
        keys.case_guidelines(case_id): prior.get("citations"),
        keys.case_contraindications(case_id): prior.get("conflicts"),
        keys.case_candidates(case_id): prior.get("candidates"),
        keys.case_simulation(case_id): prior.get("simulation"),
        keys.case_critic(case_id): prior.get("critic"),
        keys.case_medication_safety(case_id): prior.get("medication_safety"),
        keys.case_medication_conflicts(case_id): (prior.get("medication_safety") or {}).get("conflicts"),
        keys.case_medication_alternatives(case_id): (prior.get("medication_safety") or {}).get("alternative_candidates"),
    }
    for key, value in mapping.items():
        if value is not None:
            await redis_store.set_json(key, value)


async def get_run(run_id: str) -> CareGuardRun:
    state = await redis_store.get_json(keys.run_state(run_id))
    if not state:
        raise RunNotFoundError(f"No CareGuard run {run_id!r}")
    return CareGuardRun.model_validate(state["run"])


async def cancel_run(run_id: str) -> CareGuardRun:
    state = await redis_store.get_json(keys.run_state(run_id))
    if not state:
        raise RunNotFoundError(f"No CareGuard run {run_id!r}")
    run = CareGuardRun.model_validate(state["run"])
    run.status = "cancelled"
    run.updated_at = _now()
    await _save_run(run, prior_outputs=state.get("prior_outputs", {}))
    await audit.record(case_id=run.case_id, run_id=run_id, actor="careguard_orchestrator", action="cancelled run")
    return run


async def advance_run(run_id: str) -> dict[str, Any]:
    """Execute exactly one stage. Idempotent + locked."""
    state = await redis_store.get_json(keys.run_state(run_id))
    if not state:
        raise RunNotFoundError(f"No CareGuard run {run_id!r}")
    run = CareGuardRun.model_validate(state["run"])
    prior = dict(state.get("prior_outputs", {}))

    if run.status in ("completed", "cancelled", "failed"):
        return {"run": run.model_dump(), "stage_result": None, "terminal": True}

    stage_id = _next_stage(run.completed_stages)
    if stage_id is None or stage_id == STAGE_CLINICIAN_REVIEW_READY:
        return await _finalize(run, prior)

    lock_key = keys.run_lock(run_id)
    if not await redis_store.acquire_lock(lock_key, ttl=90):
        return {"run": run.model_dump(), "stage_result": None, "locked": True,
                "note": "another stage execution is in progress"}

    try:
        # Idempotency: if this stage already ran, return its cached result.
        cached = next((r for r in run.stage_results if r.stage_id == stage_id), None)
        if cached is not None:
            return {"run": run.model_dump(), "stage_result": cached.model_dump(), "idempotent_hit": True}

        ctx = await _build_context(run, prior)
        result = await _run_stage_with_retry(stage_id, ctx)

        # Persist stage result + merge its outputs.
        run.stage_results.append(result)
        run.completed_stages.append(stage_id)
        run.current_stage = stage_id
        run.next_stage = _next_stage(run.completed_stages)
        run.status = "blocked" if result.status == "blocked" else "running"
        run.warnings.extend(result.warnings)
        run.safety_flags.extend(result.safety_flags)
        run.updated_at = _now()
        prior = _merge_outputs(prior, result)

        await redis_store.set_json(keys.stage_result(run.case_id, stage_id), result.model_dump())
        aid = await audit.record(
            case_id=run.case_id, run_id=run_id, stage_id=stage_id,
            actor=result.agent_id, action=f"stage {stage_id} → {result.status}",
            detail={"latency_ms": result.latency_ms, "warnings": len(result.warnings),
                    "model_used": result.model_used},
        )
        result.audit_event_ids.append(aid)

        # A blocked encounter-intake stops the run (safety gate).
        if stage_id == "encounter_intake" and result.status == "blocked":
            run.status = "blocked"
            run.next_stage = None

        await _save_run(run, prior_outputs=prior)
        await _persist_case_artifacts(run.case_id, prior)
        # Return this stage's result now; the NEXT call finalizes when only the
        # clinician-review gate remains (so no stage result is ever swallowed).
        terminal = run.next_stage is None
        return {"run": run.model_dump(), "stage_result": result.model_dump(), "terminal": terminal}
    finally:
        await redis_store.release_lock(lock_key)


async def _finalize(run: CareGuardRun, prior: dict[str, Any]) -> dict[str, Any]:
    critic = prior.get("critic") or {}
    run.status = "completed"
    run.current_stage = STAGE_CLINICIAN_REVIEW_READY
    run.next_stage = None
    run.updated_at = _now()
    if STAGE_CLINICIAN_REVIEW_READY not in run.completed_stages:
        run.completed_stages.append(STAGE_CLINICIAN_REVIEW_READY)
    await _save_run(run, prior_outputs=prior)
    await _persist_case_artifacts(run.case_id, prior)
    await audit.record(case_id=run.case_id, run_id=run.run_id, actor="careguard_orchestrator",
                       action="run completed", detail={"safe_to_display": critic.get("safe_to_display")})
    return {
        "run": run.model_dump(),
        "stage_result": None,
        "terminal": True,
        "clinician_review_ready": True,
        "safe_to_display": critic.get("safe_to_display", False),
    }


async def _run_stage_with_retry(stage_id: str, ctx: CareGuardContext) -> CareGuardStageResult:
    agent = _AGENTS[stage_id]
    try:
        return await agent(ctx)
    except Exception:  # noqa: BLE001 — bounded single retry
        try:
            return await agent(ctx)
        except Exception as exc:  # noqa: BLE001
            raise StageExecutionError(f"stage {stage_id} failed after retry: {type(exc).__name__}", stage_id=stage_id)


async def _build_context(run: CareGuardRun, prior: dict[str, Any]) -> CareGuardContext:
    record = await redis_store.get_json(keys.case_record(run.case_id))
    case = CareGuardCase.model_validate(record) if record else CareGuardCase(case_id=run.case_id, created_at=_now())
    fhir = await redis_store.get_json(keys.case_fhir(run.case_id)) or {}
    facts = [ClinicalFact.model_validate(f) for f in (record or {}).get("facts", [])]
    return CareGuardContext(
        run_id=run.run_id,
        case_id=run.case_id,
        workflow_intent=run.workflow_intent,
        clinical_question=prior.get("clinical_question", case.clinical_question),
        facts=facts,
        prior_stage_outputs=prior,
        missing_resources=fhir.get("missing_critical_evidence", []),
    )


def _merge_outputs(prior: dict[str, Any], result: CareGuardStageResult) -> dict[str, Any]:
    out = dict(prior)
    so = result.structured_output or {}
    # Lift the keys later stages read.
    for key in ("patient_context", "review_scope", "cross_organ_matrix", "citations",
                "normalized_medications", "conflicts", "candidates", "simulation", "critic",
                "medication_safety", "bundle_id"):
        if key in so:
            out[key] = so[key]
    out[f"stage:{result.stage_id}"] = {"status": result.status, "confidence": result.confidence}
    return out


async def _save_run(run: CareGuardRun, *, prior_outputs: dict[str, Any]) -> None:
    await redis_store.set_json(
        keys.run_state(run.run_id),
        {"run": run.model_dump(), "prior_outputs": prior_outputs},
    )
    await redis_store.set_json(keys.run_stages(run.run_id),
                               [r.model_dump() for r in run.stage_results])
