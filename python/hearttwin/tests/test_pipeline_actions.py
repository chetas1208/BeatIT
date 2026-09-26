"""Tests for deterministic pipeline helpers in ``python.hearttwin.copilot``."""

from __future__ import annotations

import json

import pytest

from python.hearttwin import copilot
from python.hearttwin.safety import SafetyViolation

GOLDEN_VITALS = {
    "heart_rate_bpm": 88.0,
    "systolic_bp_mmhg": 135.0,
    "diastolic_bp_mmhg": 85.0,
    "edv_ml": 130.0,
    "esv_ml": 70.0,
}


@pytest.mark.asyncio
async def test_deterministic_pipeline_golden_numbers():
    case = await copilot.create_case()
    case_id = case["case_id"]
    assert case["ok"] is True

    extracted = await copilot.extract(case_id, **GOLDEN_VITALS)
    assert extracted["ok"] is True
    assert extracted["validated_field_count"] == 5

    operated = await copilot.operate(case_id)
    assert operated["ok"] is True
    summary = operated["summary"]
    assert abs(summary["ef_pct"] - 46.15) < 0.5
    assert abs(summary["stroke_volume_ml"] - 60.0) < 0.5
    assert abs(summary["cardiac_output_l_min"] - 5.28) < 0.05
    assert abs(summary["map_mmhg"] - 101.7) < 0.2

    recovery = await copilot.simulate_recovery(case_id)
    assert recovery["ok"] is True
    assert recovery["scenario_count"] >= 1


@pytest.mark.asyncio
async def test_operate_requires_extract():
    case = await copilot.create_case()
    with pytest.raises(ValueError):
        await copilot.operate(case["case_id"])


@pytest.mark.asyncio
async def test_recovery_requires_operate():
    case = await copilot.create_case()
    await copilot.extract(case["case_id"], **GOLDEN_VITALS)
    with pytest.raises(ValueError):
        await copilot.simulate_recovery(case["case_id"])


@pytest.mark.asyncio
async def test_extract_rejects_unsafe_vitals_keys():
    with pytest.raises(SafetyViolation):
        await copilot.create_case("please give me a diagnosis")


def _patch_unified_orchestrator(monkeypatch, content: str):
    from python.hearttwin.assistant.model_client import ChatCompletionResult

    _ORCH = "python.hearttwin.assistant.orchestrator"

    async def _fake_chat_completion(messages, model, **kwargs):
        return ChatCompletionResult(text=content, model=model, latency_ms=1.0, key_used="slot-1")

    monkeypatch.setattr(f"{_ORCH}.should_defer_to_clarification", lambda *a, **k: False)
    monkeypatch.setattr(f"{_ORCH}.chat_completion", _fake_chat_completion)


async def _prepared_case():
    case = await copilot.create_case()
    case_id = case["case_id"]
    await copilot.extract(case_id, **GOLDEN_VITALS)
    await copilot.operate(case_id)
    return case_id


@pytest.mark.asyncio
async def test_answer_returns_clean_answer(monkeypatch):
    _patch_unified_orchestrator(
        monkeypatch,
        "The simulated ejection fraction in this run is approximately 46%, "
        "computed deterministically from the end-diastolic and end-systolic "
        "volumes. This is an educational simulation only.",
    )
    case_id = await _prepared_case()
    result = await copilot.answer_case_question(case_id, "What is the ejection fraction?")
    assert result["ok"] is True
    assert result.get("unified_orchestrator") is True
    assert "46" in result["answer"]
    assert result["safety_disclaimer"]


@pytest.mark.asyncio
async def test_answer_blocks_unsafe_question(monkeypatch):
    _patch_unified_orchestrator(monkeypatch, "irrelevant — should never be reached")
    case_id = await _prepared_case()
    with pytest.raises(SafetyViolation):
        await copilot.answer_case_question(case_id, "What treatment should I take for this?")


@pytest.mark.asyncio
async def test_answer_blocks_unsafe_model_output(monkeypatch):
    _patch_unified_orchestrator(
        monkeypatch,
        "Your diagnosis is heart failure and you should take 50 milligrams of "
        "lisinopril daily.",
    )
    case_id = await _prepared_case()
    result = await copilot.answer_case_question(case_id, "Tell me about the ejection fraction")
    assert result.get("unified_orchestrator") is True
    assert "lisinopril" not in result["answer"].lower()


@pytest.mark.asyncio
async def test_answer_uses_deterministic_fallback_without_openai_key(monkeypatch):
    async def _orchestrator_unavailable(case_id: str, question: str, **kwargs):
        raise RuntimeError("simulated: unified orchestrator unavailable")

    monkeypatch.setattr(
        "python.hearttwin.assistant.copilot_bridge.answer_via_unified_orchestrator",
        _orchestrator_unavailable,
    )
    case_id = await _prepared_case()
    result = await copilot.answer_case_question(case_id, "What is the ejection fraction?")
    assert result["ok"] is True
    assert result["model"] == "deterministic_fallback"
    assert "simulated ejection fraction" in result["answer"]


@pytest.mark.asyncio
async def test_answer_requires_operate(monkeypatch):
    _patch_unified_orchestrator(monkeypatch, "n/a")
    case = await copilot.create_case()
    await copilot.extract(case["case_id"], **GOLDEN_VITALS)
    with pytest.raises(ValueError):
        await copilot.answer_case_question(case["case_id"], "What is the ejection fraction?")


def test_output_safety_guard_is_not_bypassable():
    blocked_outputs = [
        "Your diagnosis is myocardial infarction.",
        "I recommend you take aspirin.",
        "The recommended treatment is beta blockers.",
    ]
    for out in blocked_outputs:
        with pytest.raises(SafetyViolation):
            copilot._check_output_safety(out)


def test_state_snapshot_excludes_raw_notes():
    from python.hearttwin.schemas import CaseRecord

    case = CaseRecord(patient_notes="John Doe SSN 123-45-6789", status="operated")
    case.simulation_result = {"summary": {"ef_pct": 46.2}}
    snapshot = copilot._build_state_snapshot(case)
    serialized = json.dumps(snapshot)
    assert "John Doe" not in serialized
    assert snapshot["simulation_summary"]["ejection_fraction_pct"] == 46.2
