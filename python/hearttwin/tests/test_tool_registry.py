"""Tests for the Wave 2 canonical assistant tool registry.

Reuses the same fixtures/helper patterns as test_ensemble.py and
test_cardiac_findings.py (baseline_vitals from conftest.py, the same
CardiacTwinState/EnsembleRequest construction) rather than inventing new
fixtures, so these tests exercise the registry against the same shapes of
real data the rest of the suite already trusts.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from python.hearttwin.assistant.tool_registry import (
    Tool,
    ToolExecutionError,
    ToolNotFoundError,
    ToolRegistry,
    get_tool_registry,
)
from python.hearttwin.ensemble import (
    PARAMETER_BOUNDS,
    EnsembleDistributionRequest,
    EnsembleRequest,
    run_ensemble,
)
from python.hearttwin.schemas import (
    CardiacTwinState,
    CaseRecord,
    Hemodynamics,
    MeasuredValue,
    Measurements,
    ValueSource,
)
from python.hearttwin.storage.ensemble_store import create_ensemble_store
from python.hearttwin.tools.storage import store_case


def _measured(value: float, unit: str) -> MeasuredValue:
    return MeasuredValue(value=value, unit=unit, source=ValueSource.FILE_EXTRACTION, confidence=1.0)


def _state(baseline_vitals: dict) -> CardiacTwinState:
    return CardiacTwinState(
        case_id="tool-registry-fixture-case",
        created_at=datetime(2026, 1, 2, 3, 4, 5),  # noqa: DTZ001 - canonical naive fixture timestamp
        measurements=Measurements(
            heart_rate_bpm=_measured(baseline_vitals["heart_rate_bpm"], "bpm"),
            systolic_bp_mmhg=_measured(baseline_vitals["systolic_bp_mmhg"], "mmHg"),
            diastolic_bp_mmhg=_measured(baseline_vitals["diastolic_bp_mmhg"], "mmHg"),
            edv_ml=_measured(baseline_vitals["edv_ml"], "mL"),
            esv_ml=_measured(baseline_vitals["esv_ml"], "mL"),
        ),
        hemodynamics=Hemodynamics(
            preload_index=_measured(1.0, "index"),
            afterload_index=_measured(1.0, "index"),
            contractility_index=_measured(1.0, "index"),
            systemic_vascular_resistance_index=_measured(1.0, "index"),
        ),
    )


def _distribution(parameter_id: str) -> EnsembleDistributionRequest:
    defaults: dict[str, tuple[dict, dict]] = {
        "heart_rate_bpm": ({"mean": 72.0, "sd": 2.0}, {"min": 30.0, "max": 200.0}),
        "preload_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 1.5}),
        "afterload_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 2.0}),
        "contractility_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 1.5}),
        "systemic_vascular_resistance_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 2.0}),
    }
    parameters, bounds = defaults[parameter_id]
    return EnsembleDistributionRequest(
        parameter_id=parameter_id,
        family="normal",
        parameters=parameters,
        bounds=bounds,
        source="measurement",
        evidence_ids=["manual_baseline.json"],
        rationale="Tool registry test fixture",
        version="test-v1",
    )


@pytest.fixture
def persisted_ensemble(baseline_vitals: dict, tmp_path, monkeypatch) -> dict:
    """Run the real deterministic ensemble engine and persist it through the
    same SQLite store `api.py` uses, isolated to a per-test database file."""
    monkeypatch.setenv("BEATIT_ENSEMBLE_DB_PATH", str(tmp_path / "ensembles.sqlite3"))
    request = EnsembleRequest(
        origin_snapshot_id="snapshot-tool-registry",
        state=_state(baseline_vitals),
        seed=11,
        sample_count=6,
        distributions=[_distribution(parameter_id) for parameter_id in PARAMETER_BOUNDS],
        origin_quality="observed",
    )
    result = run_ensemble(request)
    create_ensemble_store().save(result["id"], result)
    return result


@pytest.fixture
async def cardiac_findings_case_id(baseline_vitals: dict) -> str:
    """Persist a case with real state + a reduced-EF visualization payload,
    the same shape `run_operation_pipeline` + `derive_findings` produce."""
    case_id = f"tool-registry-case-{uuid4()}"
    case = CaseRecord(
        case_id=case_id,
        state=_state(baseline_vitals),
        simulation_result={"summary": {"ef_pct": 32.0}, "3d_heart": {}, "electrophysiology": {}},
    )
    await store_case(case_id, case.model_dump(mode="json"))
    return case_id


# ---------------------------------------------------------------------------
# Registration / lookup mechanics
# ---------------------------------------------------------------------------


def test_default_registry_has_expected_tools_and_categories() -> None:
    registry = get_tool_registry()

    assert registry.get("get_cardiac_findings").category == "PHYSIOLOGY"
    uncertainty_names = {tool.name for tool in registry.list_tools(category="UNCERTAINTY")}
    assert uncertainty_names == {
        "get_ensemble",
        "get_ensemble_distributions",
        "get_ensemble_assumptions",
    }
    assert {tool.name for tool in registry.list_tools()} == {
        "get_cardiac_findings",
        "get_ensemble",
        "get_ensemble_distributions",
        "get_ensemble_assumptions",
    }


def test_all_registered_tools_are_t0_read_only() -> None:
    # Every candidate this wave could verify is a read; nothing computational
    # (T1) or higher was safe to register — see docs/assistant/wave2/tool-registry.md.
    assert all(tool.safety_level == "T0" for tool in get_tool_registry().list_tools())


def test_get_returns_none_for_unregistered_name() -> None:
    assert get_tool_registry().get("not_a_real_tool") is None


def test_register_rejects_unknown_category() -> None:
    with pytest.raises(ValueError, match="category"):
        Tool(
            name="bad_tool",
            description="x",
            safety_level="T0",
            category="NOT_A_REAL_CATEGORY",
            input_schema={},
            handler=lambda **_: None,
        )


def test_register_rejects_duplicate_name() -> None:
    registry = ToolRegistry()
    tool = Tool(
        name="dup",
        description="x",
        safety_level="T0",
        category="TWIN",
        input_schema={},
        handler=lambda **_: None,
    )
    registry.register(tool)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


# ---------------------------------------------------------------------------
# Execution against real data
# ---------------------------------------------------------------------------


async def test_execute_unknown_tool_raises_clear_error() -> None:
    with pytest.raises(ToolNotFoundError) as exc_info:
        await get_tool_registry().execute("does_not_exist", case_id="whatever")
    message = str(exc_info.value)
    assert "does_not_exist" in message
    assert "get_cardiac_findings" in message  # lists known tools, not just "not found"


async def test_get_cardiac_findings_executes_against_real_case(cardiac_findings_case_id: str) -> None:
    result = await get_tool_registry().execute("get_cardiac_findings", case_id=cardiac_findings_case_id)

    assert result.tool_name == "get_cardiac_findings"
    assert result.safety_level == "T0"
    payload = result.canonical_payload
    assert payload["case_id"] == cardiac_findings_case_id
    findings = payload["cardiac_findings"]["findings"]
    assert any(finding["id"] == "global_systolic" for finding in findings)
    assert payload["cardiac_findings"]["segment_model"] == "AHA 17-segment"


async def test_get_cardiac_findings_missing_case_raises_execution_error() -> None:
    with pytest.raises(ToolExecutionError, match="not found"):
        await get_tool_registry().execute("get_cardiac_findings", case_id=f"missing-{uuid4()}")


async def test_get_ensemble_executes_against_real_persisted_ensemble(persisted_ensemble: dict) -> None:
    result = await get_tool_registry().execute("get_ensemble", ensemble_id=persisted_ensemble["id"])

    assert result.tool_name == "get_ensemble"
    assert result.canonical_payload["id"] == persisted_ensemble["id"]
    assert result.canonical_payload["samples"] == persisted_ensemble["samples"]


async def test_get_ensemble_missing_id_raises_execution_error() -> None:
    with pytest.raises(ToolExecutionError, match="not found"):
        await get_tool_registry().execute("get_ensemble", ensemble_id=f"missing-{uuid4()}")


async def test_get_ensemble_distributions_matches_stored_distributions(persisted_ensemble: dict) -> None:
    result = await get_tool_registry().execute(
        "get_ensemble_distributions", ensemble_id=persisted_ensemble["id"]
    )

    assert result.canonical_payload == {
        "ensemble_id": persisted_ensemble["id"],
        "distributions": persisted_ensemble["distributions"],
        "provenance": persisted_ensemble["provenance"],
        "safety_disclaimer": persisted_ensemble["safety_disclaimer"],
    }


async def test_get_ensemble_assumptions_returns_real_provenance_text(persisted_ensemble: dict) -> None:
    result = await get_tool_registry().execute(
        "get_ensemble_assumptions", ensemble_id=persisted_ensemble["id"]
    )

    assumptions = result.canonical_payload["assumptions"]
    assert assumptions == persisted_ensemble["provenance"]["assumptions"]
    assert any("independently" in text for text in assumptions)
    assert result.canonical_payload["origin_quality"] == "observed"
