"""Programmatic case Q&A must route through the unified orchestrator."""

from __future__ import annotations

import pytest

from python.hearttwin.copilot import answer_case_question
from python.hearttwin.schemas import CaseRecord
from python.hearttwin.tools.storage import store_case
from datetime import datetime
from python.hearttwin.schemas import CardiacTwinState, Hemodynamics, MeasuredValue, Measurements, ValueSource


@pytest.mark.asyncio
async def test_answer_case_question_uses_unified_orchestrator_flag(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "")
    case_id = "bridge-case-1"
    state = CardiacTwinState(
        case_id=case_id,
        created_at=datetime(2026, 1, 1),  # noqa: DTZ001
        measurements=Measurements(
            heart_rate_bpm=MeasuredValue(value=70, unit="bpm", source=ValueSource.FILE_EXTRACTION, confidence=1.0),
            systolic_bp_mmhg=MeasuredValue(value=120, unit="mmHg", source=ValueSource.FILE_EXTRACTION, confidence=1.0),
            diastolic_bp_mmhg=MeasuredValue(value=80, unit="mmHg", source=ValueSource.FILE_EXTRACTION, confidence=1.0),
            edv_ml=MeasuredValue(value=120, unit="mL", source=ValueSource.FILE_EXTRACTION, confidence=1.0),
            esv_ml=MeasuredValue(value=70, unit="mL", source=ValueSource.FILE_EXTRACTION, confidence=1.0),
        ),
        hemodynamics=Hemodynamics(
            preload_index=MeasuredValue(value=1, unit="index", source=ValueSource.FILE_EXTRACTION, confidence=1.0),
            afterload_index=MeasuredValue(value=1, unit="index", source=ValueSource.FILE_EXTRACTION, confidence=1.0),
            contractility_index=MeasuredValue(value=1, unit="index", source=ValueSource.FILE_EXTRACTION, confidence=1.0),
            systemic_vascular_resistance_index=MeasuredValue(value=1, unit="index", source=ValueSource.FILE_EXTRACTION, confidence=1.0),
        ),
    )
    await store_case(
        case_id,
        CaseRecord(
            case_id=case_id,
            state=state,
            simulation_result={"summary": {"ef_pct": 42.0, "stroke_volume_ml": 50.0}},
            status="operated",
        ).model_dump(mode="json"),
    )
    result = await answer_case_question(case_id, "What is the educational purpose of this simulation?")
    assert result.get("unified_orchestrator") is True
    assert result.get("answer")
    assert result.get("safety_disclaimer")
