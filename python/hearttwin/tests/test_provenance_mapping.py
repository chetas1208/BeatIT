"""Tests for the Wave 3 legacy-provenance-vocabulary mapping layer.

Fixture patterns (`_measured`, `_state`, `_distribution`, `persisted_ensemble`,
`cardiac_findings_case_id`) mirror `test_tool_registry.py` deliberately --
this module exercises real data shaped exactly like Wave 2's tool registry
already trusts, rather than inventing new fixtures.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from python.hearttwin.assistant.provenance_mapping import (
    UnmappedProvenanceValueError,
    build_provenance_ref,
    get_provenance_for_cardiac_findings,
    get_provenance_for_ensemble,
    map_origin_quality_to_canonical,
    map_value_source_to_canonical,
)
from python.hearttwin.assistant.schemas import CanonicalProvenanceKind, ProvenanceRef
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
    SourceMapEntry,
    ValueSource,
)
from python.hearttwin.storage.ensemble_store import create_ensemble_store
from python.hearttwin.tools.storage import store_case


def _measured(value: float, unit: str, source: ValueSource = ValueSource.FILE_EXTRACTION) -> MeasuredValue:
    return MeasuredValue(value=value, unit=unit, source=source, confidence=1.0)


def _state(baseline_vitals: dict) -> CardiacTwinState:
    return CardiacTwinState(
        case_id="provenance-mapping-fixture-case",
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
        rationale="Provenance mapping test fixture",
        version="test-v1",
    )


@pytest.fixture
def persisted_ensemble(baseline_vitals: dict, tmp_path, monkeypatch) -> dict:
    """Run the real deterministic ensemble engine and persist it through the
    same SQLite store `api.py` uses, isolated to a per-test database file."""
    monkeypatch.setenv("BEATIT_ENSEMBLE_DB_PATH", str(tmp_path / "ensembles.sqlite3"))
    request = EnsembleRequest(
        origin_snapshot_id="snapshot-provenance-mapping",
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
    """Persist a case with real state (including a source_map entry for the
    damage zone) + a reduced-EF, widened-QRS visualization payload, so
    derive_findings() produces findings both with and without a matching
    source_map field."""
    case_id = f"provenance-mapping-case-{uuid4()}"
    state = _state(baseline_vitals)
    state.tissue_state.damage_zone_location = "anterior"
    state.source_map = [
        SourceMapEntry(
            field="tissue_state.damage_zone_location",
            value=None,
            unit="",
            source=ValueSource.USER_INPUT,
            confidence=0.9,
            method="clinician_annotation",
            evidence="physician-entered damage zone",
        ),
    ]
    case = CaseRecord(
        case_id=case_id,
        state=state,
        simulation_result={
            "summary": {"ef_pct": 32.0},
            "3d_heart": {},
            "electrophysiology": {"qrs_duration_ms": 140.0},
        },
    )
    await store_case(case_id, case.model_dump(mode="json"))
    return case_id


# ---------------------------------------------------------------------------
# map_value_source_to_canonical -- completeness + rejection
# ---------------------------------------------------------------------------


def test_every_value_source_member_maps_without_raising() -> None:
    for member in ValueSource:
        result = map_value_source_to_canonical(member)
        assert isinstance(result, CanonicalProvenanceKind)


def test_value_source_mapping_table_is_exact() -> None:
    assert map_value_source_to_canonical(ValueSource.FILE_EXTRACTION) == CanonicalProvenanceKind.OBSERVED
    assert map_value_source_to_canonical(ValueSource.USER_INPUT) == CanonicalProvenanceKind.USER_ASSERTED
    assert map_value_source_to_canonical(ValueSource.DEFAULT_MODEL_PRIOR) == CanonicalProvenanceKind.MODEL_PRIOR
    assert map_value_source_to_canonical(ValueSource.DERIVED) == CanonicalProvenanceKind.DERIVED


def test_value_source_mapping_rejects_unrecognized_value() -> None:
    with pytest.raises(UnmappedProvenanceValueError):
        map_value_source_to_canonical("not_a_real_source")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# map_origin_quality_to_canonical -- completeness + rejection
# ---------------------------------------------------------------------------


def test_every_origin_quality_value_maps_without_raising() -> None:
    for value in ("observed", "derived", "interpolated", "synthetic"):
        result = map_origin_quality_to_canonical(value)
        assert isinstance(result, CanonicalProvenanceKind)


def test_origin_quality_mapping_table_is_exact() -> None:
    assert map_origin_quality_to_canonical("observed") == CanonicalProvenanceKind.OBSERVED
    assert map_origin_quality_to_canonical("derived") == CanonicalProvenanceKind.DERIVED
    assert map_origin_quality_to_canonical("interpolated") == CanonicalProvenanceKind.DERIVED
    assert map_origin_quality_to_canonical("synthetic") == CanonicalProvenanceKind.SIMULATED


def test_origin_quality_mapping_rejects_unrecognized_value() -> None:
    with pytest.raises(UnmappedProvenanceValueError):
        map_origin_quality_to_canonical("not_a_real_quality")


# ---------------------------------------------------------------------------
# build_provenance_ref
# ---------------------------------------------------------------------------


def test_build_provenance_ref_from_value_source() -> None:
    ref = build_provenance_ref(
        "schemas.py:SourceMapEntry",
        ValueSource.DERIVED,
        "ejection_fraction_pct",
        source_id="field-1",
        confidence=0.85,
    )
    assert isinstance(ref, ProvenanceRef)
    assert ref.kind == CanonicalProvenanceKind.DERIVED
    assert ref.source_id == "field-1"
    assert ref.confidence == 0.85
    assert "ejection_fraction_pct" in ref.description


def test_build_provenance_ref_from_origin_quality() -> None:
    ref = build_provenance_ref(
        "ensemble.py:EnsembleProvenance",
        "synthetic",
        "origin snapshot quality",
    )
    assert ref.kind == CanonicalProvenanceKind.SIMULATED


# ---------------------------------------------------------------------------
# get_provenance_for_ensemble -- real persisted ensemble data
# ---------------------------------------------------------------------------


async def test_get_provenance_for_ensemble_returns_nonempty_typed_refs(persisted_ensemble: dict) -> None:
    refs = await get_provenance_for_ensemble(persisted_ensemble["id"])

    assert refs
    assert all(isinstance(ref, ProvenanceRef) for ref in refs)
    # origin_quality="observed" -> OBSERVED must be present.
    assert any(ref.kind == CanonicalProvenanceKind.OBSERVED for ref in refs)
    # Real assumption text from ensemble.py:441 must survive into a ref.
    assumption_refs = [ref for ref in refs if ref.kind == CanonicalProvenanceKind.MODEL_PRIOR]
    assert assumption_refs
    assert any("independently" in (ref.description or "") for ref in assumption_refs)


async def test_get_provenance_for_ensemble_maps_evidence_ids_as_external_reference(persisted_ensemble: dict) -> None:
    refs = await get_provenance_for_ensemble(persisted_ensemble["id"])

    external_refs = [ref for ref in refs if ref.kind == CanonicalProvenanceKind.EXTERNAL_REFERENCE]
    stored_evidence_ids = set(persisted_ensemble["provenance"]["evidence_ids"])
    assert stored_evidence_ids  # fixture distributions carry evidence_ids
    assert {ref.source_id for ref in external_refs} == stored_evidence_ids


async def test_get_provenance_for_ensemble_missing_id_raises() -> None:
    with pytest.raises(RuntimeError, match="not found"):
        await get_provenance_for_ensemble(f"missing-{uuid4()}")


# ---------------------------------------------------------------------------
# get_provenance_for_cardiac_findings -- real derived findings
# ---------------------------------------------------------------------------


async def test_get_provenance_for_cardiac_findings_returns_nonempty_typed_refs(
    cardiac_findings_case_id: str,
) -> None:
    refs = await get_provenance_for_cardiac_findings(cardiac_findings_case_id)

    assert refs
    assert all(isinstance(ref, ProvenanceRef) for ref in refs)


async def test_get_provenance_for_cardiac_findings_traces_source_map_field(
    cardiac_findings_case_id: str,
) -> None:
    refs = await get_provenance_for_cardiac_findings(cardiac_findings_case_id)

    # The regional finding traces to the fixture's USER_INPUT source_map
    # entry for tissue_state.damage_zone_location -> USER_ASSERTED.
    regional_refs = [ref for ref in refs if ref.source_id == "regional_anterior"]
    assert regional_refs
    assert regional_refs[0].kind == CanonicalProvenanceKind.USER_ASSERTED
    assert regional_refs[0].confidence == 0.9


async def test_get_provenance_for_cardiac_findings_defaults_pipeline_output_to_derived(
    cardiac_findings_case_id: str,
) -> None:
    refs = await get_provenance_for_cardiac_findings(cardiac_findings_case_id)

    # global_systolic comes from visualization.summary.ef_pct, which has no
    # source_map field -- must fall back to DERIVED, not raise or skip.
    global_refs = [ref for ref in refs if ref.source_id == "global_systolic"]
    assert global_refs
    assert global_refs[0].kind == CanonicalProvenanceKind.DERIVED


async def test_get_provenance_for_cardiac_findings_missing_case_raises() -> None:
    with pytest.raises(RuntimeError, match="not found"):
        await get_provenance_for_cardiac_findings(f"missing-{uuid4()}")
