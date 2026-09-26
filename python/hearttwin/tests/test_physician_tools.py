"""Tests for the Wave 3 physician-tooling additions.

Reuses `test_tool_registry.py`'s own fixture helpers (`_state`, `_distribution`,
`persisted_ensemble`, `cardiac_findings_case_id`) instead of inventing new
ones, per this wave's brief, since they already build the same real
CardiacTwinState / EnsembleRequest shapes the rest of the suite trusts.

Two isolation strategies are used, deliberately:

- `get_raw_provenance_ledger` / `get_pv_loop` only ever call
  `python.hearttwin.tools.storage.get_case` — never the global tool
  registry — so they are exercised against a throwaway `ToolRegistry()`
  instance, never touching the process-wide singleton at all.
- `get_findings_by_region` / `get_ensemble_summary` are composite tools whose
  handlers call the real `get_tool_registry()` singleton internally (by
  design — see physician_tools.py's module docstring: composition should go
  through the one true registry, not a side channel). To exercise them
  without permanently mutating that singleton for the rest of the test
  session — which would break `test_tool_registry.py`'s exact-set assertion
  on the same singleton — `_reset_global_tool_registry` forces the module
  global back to `None` before and after every test in this file, so
  whichever test file runs next always sees a freshly rebuilt, physician-
  tools-free registry.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from python.hearttwin.assistant import tool_registry as tool_registry_module
from python.hearttwin.assistant.physician_tools import register_physician_tools
from python.hearttwin.assistant.tool_registry import (
    ToolExecutionError,
    ToolRegistry,
    get_tool_registry,
)
from python.hearttwin.ensemble import PARAMETER_BOUNDS, EnsembleRequest, run_ensemble
from python.hearttwin.schemas import CaseRecord
from python.hearttwin.storage.ensemble_store import create_ensemble_store
from python.hearttwin.tests.test_tool_registry import (
    _distribution,
    _state,
    cardiac_findings_case_id,  # noqa: F401 - reused as a pytest fixture
)
from python.hearttwin.tools.storage import store_case


@pytest.fixture(autouse=True)
def _reset_global_tool_registry():
    """Guarantee the process-wide singleton is pristine before AND after every
    test here, so composite-tool tests (which must use the real singleton —
    see module docstring) never leak physician tools into any other test
    file's assertions about `get_tool_registry()`'s exact contents."""
    tool_registry_module._REGISTRY = None
    yield
    tool_registry_module._REGISTRY = None


@pytest.fixture
def fresh_registry() -> ToolRegistry:
    """A throwaway registry, isolated from the process-wide singleton, for
    tools whose handlers only touch case/ensemble storage directly."""
    registry = ToolRegistry()
    register_physician_tools(registry)
    return registry


@pytest.fixture
async def pv_loop_case_id(baseline_vitals: dict) -> str:
    """Persist a case with real state + a simulation_result carrying the same
    `pv_loop` shape `run_hemodynamics_agent` produces
    (agents/hemodynamics_agent.py:672-686)."""
    case_id = f"pv-loop-case-{uuid4()}"
    case = CaseRecord(
        case_id=case_id,
        state=_state(baseline_vitals),
        simulation_result={
            "pv_loop": {
                "volume_ml": [120.0, 110.0, 80.0, 120.0],
                "pressure_mmhg": [8.0, 90.0, 130.0, 8.0],
                "loop_area_index": 0.42,
                "pv_loop_area_mmhg_ml": 1680.0,
                "ef_pct": 33.3,
                "peak_pressure_mmhg": 130.0,
                "stroke_work_j": 1.2,
                "model": "time-varying-elastance-v1",
                "simulation_label": "educational simulation",
                "pv_warnings": ["Educational simulation only — results are not for clinical use"],
            },
            "summary": {"ef_pct": 33.3},
        },
    )
    await store_case(case_id, case.model_dump(mode="json"))
    return case_id


@pytest.fixture
def persisted_ensemble(baseline_vitals: dict, tmp_path, monkeypatch) -> dict:
    """Same construction as test_tool_registry.py's fixture of the same name
    (not imported directly since it also depends on that module's own
    `_state`/`_distribution` closures over this file's fixtures)."""
    monkeypatch.setenv("BEATIT_ENSEMBLE_DB_PATH", str(tmp_path / "ensembles.sqlite3"))
    request = EnsembleRequest(
        origin_snapshot_id="snapshot-physician-tools",
        state=_state(baseline_vitals),
        seed=11,
        sample_count=6,
        distributions=[_distribution(parameter_id) for parameter_id in PARAMETER_BOUNDS],
        origin_quality="observed",
    )
    result = run_ensemble(request)
    create_ensemble_store().save(result["id"], result)
    return result


# ---------------------------------------------------------------------------
# get_raw_provenance_ledger
# ---------------------------------------------------------------------------


async def test_get_raw_provenance_ledger_executes_against_real_case(
    fresh_registry: ToolRegistry, baseline_vitals: dict
) -> None:
    case_id = f"provenance-case-{uuid4()}"
    case = CaseRecord(case_id=case_id, state=_state(baseline_vitals))
    await store_case(case_id, case.model_dump(mode="json"))

    result = await fresh_registry.execute("get_raw_provenance_ledger", case_id=case_id)

    assert result.tool_name == "get_raw_provenance_ledger"
    assert result.safety_level == "T0"
    payload = result.canonical_payload
    assert payload["case_id"] == case_id
    assert payload["scope"] == "raw"
    # CardiacTwinState() defaults to an empty source_map when no file/manual
    # extraction populated one — the ledger being a real (possibly empty)
    # list, not a fabricated one, is the point of this assertion.
    assert payload["provenance_ledger"] == []


async def test_get_raw_provenance_ledger_missing_case_raises_execution_error(
    fresh_registry: ToolRegistry,
) -> None:
    with pytest.raises(ToolExecutionError, match="not found"):
        await fresh_registry.execute("get_raw_provenance_ledger", case_id=f"missing-{uuid4()}")


async def test_get_raw_provenance_ledger_no_state_raises_execution_error(
    fresh_registry: ToolRegistry,
) -> None:
    case_id = f"no-state-case-{uuid4()}"
    await store_case(case_id, CaseRecord(case_id=case_id).model_dump(mode="json"))

    with pytest.raises(ToolExecutionError, match="no simulated state"):
        await fresh_registry.execute("get_raw_provenance_ledger", case_id=case_id)


# ---------------------------------------------------------------------------
# get_findings_by_region
# ---------------------------------------------------------------------------


async def test_get_findings_by_region_filters_real_findings(cardiac_findings_case_id: str) -> None:
    registry = register_physician_tools(get_tool_registry())

    result = await registry.execute(
        "get_findings_by_region", case_id=cardiac_findings_case_id, region="Left ventricle"
    )

    payload = result.canonical_payload
    assert payload["match_count"] >= 1
    assert all(
        "left ventricle" in str(finding.get("region") or "").lower()
        for finding in payload["matched_findings"]
    )
    assert any(finding["id"] == "global_systolic" for finding in payload["matched_findings"])


async def test_get_findings_by_region_no_match_returns_empty(cardiac_findings_case_id: str) -> None:
    registry = register_physician_tools(get_tool_registry())

    result = await registry.execute(
        "get_findings_by_region", case_id=cardiac_findings_case_id, region="nonexistent-region-xyz"
    )

    assert result.canonical_payload["matched_findings"] == []
    assert result.canonical_payload["match_count"] == 0


async def test_get_findings_by_region_propagates_missing_case_error() -> None:
    registry = register_physician_tools(get_tool_registry())

    with pytest.raises(ToolExecutionError, match="not found"):
        await registry.execute(
            "get_findings_by_region", case_id=f"missing-{uuid4()}", region="anything"
        )


# ---------------------------------------------------------------------------
# get_pv_loop
# ---------------------------------------------------------------------------


async def test_get_pv_loop_executes_against_real_case(
    fresh_registry: ToolRegistry, pv_loop_case_id: str
) -> None:
    result = await fresh_registry.execute("get_pv_loop", case_id=pv_loop_case_id)

    assert result.tool_name == "get_pv_loop"
    assert result.safety_level == "T0"
    payload = result.canonical_payload
    assert payload["case_id"] == pv_loop_case_id
    assert payload["pv_loop"]["ef_pct"] == 33.3
    assert payload["pv_loop"]["volume_ml"] == [120.0, 110.0, 80.0, 120.0]
    assert "scenario" in payload["note"].lower()


async def test_get_pv_loop_missing_simulation_result_raises_execution_error(
    fresh_registry: ToolRegistry, baseline_vitals: dict
) -> None:
    case_id = f"no-sim-case-{uuid4()}"
    case = CaseRecord(case_id=case_id, state=_state(baseline_vitals))
    await store_case(case_id, case.model_dump(mode="json"))

    with pytest.raises(ToolExecutionError, match="no simulation result"):
        await fresh_registry.execute("get_pv_loop", case_id=case_id)


async def test_get_pv_loop_missing_case_raises_execution_error(fresh_registry: ToolRegistry) -> None:
    with pytest.raises(ToolExecutionError, match="not found"):
        await fresh_registry.execute("get_pv_loop", case_id=f"missing-{uuid4()}")


# ---------------------------------------------------------------------------
# get_ensemble_summary (composite tool)
# ---------------------------------------------------------------------------


async def test_get_ensemble_summary_combines_real_tool_outputs(persisted_ensemble: dict) -> None:
    registry = register_physician_tools(get_tool_registry())

    result = await registry.execute("get_ensemble_summary", ensemble_id=persisted_ensemble["id"])

    assert result.tool_name == "get_ensemble_summary"
    payload = result.canonical_payload
    assert payload["ensemble_id"] == persisted_ensemble["id"]
    # Each sub-payload matches exactly what calling the three underlying real
    # tools directly returns (test_tool_registry.py asserts the same shapes).
    assert payload["ensemble"]["id"] == persisted_ensemble["id"]
    assert payload["ensemble"]["samples"] == persisted_ensemble["samples"]
    assert payload["distributions"]["distributions"] == persisted_ensemble["distributions"]
    assert payload["assumptions"]["assumptions"] == persisted_ensemble["provenance"]["assumptions"]
    assert payload["assumptions"]["origin_quality"] == "observed"


async def test_get_ensemble_summary_missing_ensemble_raises_execution_error() -> None:
    registry = register_physician_tools(get_tool_registry())

    with pytest.raises(ToolExecutionError, match="not found"):
        await registry.execute("get_ensemble_summary", ensemble_id=f"missing-{uuid4()}")


# ---------------------------------------------------------------------------
# Registration mechanics
# ---------------------------------------------------------------------------


def test_register_physician_tools_is_idempotent() -> None:
    registry = ToolRegistry()
    register_physician_tools(registry)
    register_physician_tools(registry)  # must not raise "already registered"

    assert {tool.name for tool in registry.list_tools()} == {
        "get_raw_provenance_ledger",
        "get_findings_by_region",
        "get_pv_loop",
        "get_ensemble_summary",
    }


def test_register_physician_tools_defaults_to_the_real_singleton() -> None:
    registry = register_physician_tools()

    assert registry is get_tool_registry()
    names = {tool.name for tool in registry.list_tools()}
    assert {"get_raw_provenance_ledger", "get_findings_by_region", "get_pv_loop", "get_ensemble_summary"} <= names
    # And Wave 2's own four tools are still present, untouched, on the same
    # single registry — this file adds to it, it does not replace it.
    assert {"get_cardiac_findings", "get_ensemble", "get_ensemble_distributions", "get_ensemble_assumptions"} <= names


def test_all_physician_tools_are_t0_read_only() -> None:
    registry = ToolRegistry()
    register_physician_tools(registry)

    assert all(tool.safety_level == "T0" for tool in registry.list_tools())
