"""Shadow Trial + Missing Piece tools for the ONE canonical assistant registry."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from python.hearttwin.assistant.tool_registry import (
    Tool,
    ToolExecutionError,
    ToolRegistry,
    get_tool_registry,
)
from python.hearttwin.assistant.schemas import ExecutionClass
from python.hearttwin.missing_piece.engine import run_missing_piece
from python.hearttwin.shadow_trial_contracts import (
    ScenarioDefinition,
    ScenarioParameterChange,
    ShadowTrialResult,
)
from python.hearttwin.shadow_trial_engine import run_shadow_trial
from python.hearttwin.storage.ensemble_store import EnsembleStoreError, create_ensemble_store
from python.hearttwin.storage.missing_piece_store import MissingPieceStoreError, create_missing_piece_store
from python.hearttwin.storage.shadow_trial_store import ShadowTrialStoreError, create_shadow_trial_store


async def _load_ensemble(ensemble_id: str) -> dict[str, Any]:
    store = create_ensemble_store()
    try:
        result = await asyncio.to_thread(store.get, ensemble_id)
    except (EnsembleStoreError, OSError) as exc:
        raise ToolExecutionError("ensemble persistence is unavailable") from exc
    if result is None:
        raise ToolExecutionError(f"ensemble {ensemble_id!r} not found")
    return result


def _default_afterload_scenario(origin_snapshot_id: str) -> ScenarioDefinition:
    return ScenarioDefinition(
        id="assistant-afterload-bump",
        label="Bounded afterload hypothetical (assistant default)",
        origin_snapshot_id=origin_snapshot_id,
        parameters=[
            ScenarioParameterChange(
                parameter="afterload_index",
                value=1.2,
                baseline=1.0,
                delta=0.2,
                unit="index",
            )
        ],
    )


async def _handle_run_shadow_trial(*, baseline_ensemble_id: str) -> dict[str, Any]:
    baseline = await _load_ensemble(baseline_ensemble_id)
    origin = baseline.get("origin_snapshot_id")
    if not origin:
        raise ToolExecutionError("ensemble lacks origin_snapshot_id for scenario binding")
    scenario = _default_afterload_scenario(str(origin))
    result = run_shadow_trial(baseline, scenario)
    payload = result.model_dump(mode="json")
    store = create_shadow_trial_store()
    try:
        await asyncio.to_thread(store.save, result.id, payload)
    except (ShadowTrialStoreError, OSError) as exc:
        raise ToolExecutionError("shadow trial persistence failed") from exc
    return {
        "shadow_trial_id": result.id,
        "status": result.status,
        "valid_pairs": result.valid_pairs,
        "requested_pairs": result.requested_pairs,
        "safety_disclaimer": result.safety_disclaimer,
    }


async def _handle_get_shadow_trial(*, shadow_trial_id: str) -> dict[str, Any]:
    store = create_shadow_trial_store()
    try:
        payload = await asyncio.to_thread(store.get, shadow_trial_id)
    except (ShadowTrialStoreError, OSError) as exc:
        raise ToolExecutionError("shadow trial persistence is unavailable") from exc
    if payload is None:
        raise ToolExecutionError(f"shadow trial {shadow_trial_id!r} not found")
    result = ShadowTrialResult.model_validate(payload)
    return result.model_dump(mode="json")


async def _handle_run_missing_piece(*, baseline_ensemble_id: str, target_metric: str) -> dict[str, Any]:
    baseline = await _load_ensemble(baseline_ensemble_id)
    result = run_missing_piece(baseline, target_metric)
    payload = result.model_dump(mode="json")
    store = create_missing_piece_store()
    analysis_id = result.provenance.analysis_id
    try:
        await asyncio.to_thread(store.save, analysis_id, payload)
    except (MissingPieceStoreError, OSError) as exc:
        raise ToolExecutionError("missing piece persistence failed") from exc
    return {
        "missing_piece_id": analysis_id,
        "target_metric": result.target_metric,
        "dominant_uncertainty_drivers": result.dominant_uncertainty_drivers,
        "evidence_ranking": result.evidence_ranking,
        "safety_disclaimer": result.safety_disclaimer,
    }


async def _handle_get_missing_piece(*, missing_piece_id: str) -> dict[str, Any]:
    store = create_missing_piece_store()
    try:
        payload = await asyncio.to_thread(store.get, missing_piece_id)
    except (MissingPieceStoreError, OSError) as exc:
        raise ToolExecutionError("missing piece persistence is unavailable") from exc
    if payload is None:
        raise ToolExecutionError(f"missing piece analysis {missing_piece_id!r} not found")
    return payload


_SIMULATION_TOOLS: tuple[Tool, ...] = (
    Tool(
        name="run_shadow_trial",
        description=(
            "Run a paired Shadow Trial on a persisted baseline ensemble using the "
            "canonical default afterload scenario (educational simulation only)."
        ),
        safety_level="T1",
        category="EXPERIMENT",
        input_schema={
            "type": "object",
            "properties": {
                "baseline_ensemble_id": {"type": "string"},
            },
            "required": ["baseline_ensemble_id"],
        },
        handler=_handle_run_shadow_trial,
        execution_class=ExecutionClass.SIMULATION,
    ),
    Tool(
        name="get_shadow_trial",
        description="Load a persisted Shadow Trial result by id.",
        safety_level="T0",
        category="EXPERIMENT",
        input_schema={
            "type": "object",
            "properties": {"shadow_trial_id": {"type": "string"}},
            "required": ["shadow_trial_id"],
        },
        handler=_handle_get_shadow_trial,
        execution_class=ExecutionClass.EVIDENCE_RETRIEVAL,
    ),
    Tool(
        name="run_missing_piece",
        description=(
            "Run Missing Piece uncertainty/evidence-priority analysis for a target metric "
            "on a persisted baseline ensemble."
        ),
        safety_level="T1",
        category="UNCERTAINTY",
        input_schema={
            "type": "object",
            "properties": {
                "baseline_ensemble_id": {"type": "string"},
                "target_metric": {"type": "string"},
            },
            "required": ["baseline_ensemble_id", "target_metric"],
        },
        handler=_handle_run_missing_piece,
        execution_class=ExecutionClass.DETERMINISTIC_COMPUTATION,
    ),
    Tool(
        name="get_missing_piece",
        description="Load a persisted Missing Piece analysis by id.",
        safety_level="T0",
        category="UNCERTAINTY",
        input_schema={
            "type": "object",
            "properties": {"missing_piece_id": {"type": "string"}},
            "required": ["missing_piece_id"],
        },
        handler=_handle_get_missing_piece,
        execution_class=ExecutionClass.EVIDENCE_RETRIEVAL,
    ),
)


def register_simulation_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    target = registry if registry is not None else get_tool_registry()
    for tool in _SIMULATION_TOOLS:
        if target.get(tool.name) is None:
            target.register(tool)
    return target
