"""Tests for the Wave 3 physician-brief generator.

Fixtures mirror test_tool_registry.py's pattern (same baseline_vitals
fixture from conftest.py, same CardiacTwinState/EnsembleRequest
construction, same persisted-store approach) rather than inventing new
fixture shapes — this exercises generate_physician_brief against the same
real data the rest of the suite already trusts, not synthetic stand-ins.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from python.hearttwin.assistant.physician_brief import (
    DecisionSupportBundle,
    generate_physician_brief,
    scan_bundle_strings,
)
from python.hearttwin.assistant.schemas import (
    AssistantArtifactType,
    ConversationContext,
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
        case_id="physician-brief-fixture-case",
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
        rationale="Physician brief test fixture",
        version="test-v1",
    )


@pytest.fixture
def persisted_ensemble(baseline_vitals: dict, tmp_path, monkeypatch) -> dict:
    """Run the real deterministic ensemble engine and persist it through the
    same SQLite store api.py uses, isolated to a per-test database file."""
    monkeypatch.setenv("BEATIT_ENSEMBLE_DB_PATH", str(tmp_path / "ensembles.sqlite3"))
    request = EnsembleRequest(
        origin_snapshot_id="snapshot-physician-brief",
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
async def reduced_ef_case_id(baseline_vitals: dict) -> str:
    """Persist a case with real state + a reduced-EF visualization payload,
    the same shape run_operation_pipeline + derive_findings produce."""
    case_id = f"physician-brief-case-{uuid4()}"
    case = CaseRecord(
        case_id=case_id,
        state=_state(baseline_vitals),
        simulation_result={"summary": {"ef_pct": 32.0}, "3d_heart": {}, "electrophysiology": {}},
    )
    await store_case(case_id, case.model_dump(mode="json"))
    return case_id


@pytest.fixture
def physician_context() -> ConversationContext:
    return ConversationContext(conversation_id="conv-1", audience="physician", patient_id="patient-1")


# ---------------------------------------------------------------------------
# (a) well-formed artifact from real data
# ---------------------------------------------------------------------------


async def test_generate_physician_brief_produces_well_formed_artifact(
    reduced_ef_case_id: str, persisted_ensemble: dict, physician_context: ConversationContext
) -> None:
    artifact = await generate_physician_brief(
        reduced_ef_case_id, persisted_ensemble["id"], physician_context
    )

    assert artifact.type is AssistantArtifactType.PHYSICIAN_BRIEF
    assert artifact.conversation_id == "conv-1"
    assert artifact.patient_id == "patient-1"
    assert "get_cardiac_findings" in artifact.source_tool_ids
    assert "get_ensemble_distributions" in artifact.source_tool_ids
    assert "get_ensemble_assumptions" in artifact.source_tool_ids

    bundle = DecisionSupportBundle.model_validate(artifact.payload)
    assert bundle.clinical_context["case_id"] == reduced_ef_case_id
    assert bundle.clinical_context["ensemble_id"] == persisted_ensemble["id"]
    # The fixture's ef_pct=32.0 triggers derive_findings()'s "global_systolic"
    # finding (severe/moderate EF-reduction band) — confirm it made it through
    # into derived_evidence with a real claim/detail, not an empty stub.
    assert any("ejection fraction" in (entry["claim"] or "").lower() for entry in bundle.derived_evidence)
    assert all(entry["claim"] and entry["detail"] for entry in bundle.derived_evidence)


async def test_generate_physician_brief_without_ensemble_still_works(
    reduced_ef_case_id: str, physician_context: ConversationContext
) -> None:
    artifact = await generate_physician_brief(reduced_ef_case_id, None, physician_context)

    bundle = DecisionSupportBundle.model_validate(artifact.payload)
    assert bundle.simulated_results == []
    assert bundle.uncertainty == []
    assert bundle.assumptions == []
    assert any("No ensemble_id was supplied" in text for text in bundle.limitations)
    assert artifact.source_tool_ids == ["get_cardiac_findings"]


async def test_no_recommended_treatment_field_exists_anywhere() -> None:
    # Structural guarantee: the field literally does not exist on the model,
    # under this name or any close variant.
    field_names = set(DecisionSupportBundle.model_fields)
    forbidden = {"recommended_treatment", "treatment", "recommendation", "recommendations", "therapy"}
    assert field_names.isdisjoint(forbidden)


# ---------------------------------------------------------------------------
# (b) assumptions match real ensemble data exactly
# ---------------------------------------------------------------------------


async def test_assumptions_match_real_ensemble_assumptions_exactly(
    reduced_ef_case_id: str, persisted_ensemble: dict, physician_context: ConversationContext
) -> None:
    artifact = await generate_physician_brief(
        reduced_ef_case_id, persisted_ensemble["id"], physician_context
    )
    bundle = DecisionSupportBundle.model_validate(artifact.payload)

    assert bundle.assumptions == persisted_ensemble["provenance"]["assumptions"]
    assert len(bundle.assumptions) > 0


# ---------------------------------------------------------------------------
# (c) limitations are non-empty and name real, current gaps
# ---------------------------------------------------------------------------


async def test_limitations_are_nonempty_and_name_real_gaps(
    reduced_ef_case_id: str, persisted_ensemble: dict, physician_context: ConversationContext
) -> None:
    artifact = await generate_physician_brief(
        reduced_ef_case_id, persisted_ensemble["id"], physician_context
    )
    bundle = DecisionSupportBundle.model_validate(artifact.payload)

    assert len(bundle.limitations) > 0
    joined = " ".join(bundle.limitations)
    assert "Longitudinal" in joined
    assert "sensitivity" in joined.lower() or "dominant-assumption" in joined
    assert "missing_evidence" in joined
    assert "conflicts" in joined
    assert "possible_interpretations" in joined


# ---------------------------------------------------------------------------
# (d) check_output_safety passes on every generated (module-authored) string,
#     and the ONLY tolerated blocks anywhere in the bundle are the two
#     documented, pre-existing, verified-benign disclaiming-language matches
#     — never anything resembling actual treatment-recommendation language.
# ---------------------------------------------------------------------------


_TREATMENT_SIGNAL_SUBSTRINGS = (
    "recommend",
    "prescrib",
    "should take",
    "should start",
    "should stop",
    "you have",
    "you are diagnosed",
    "milligram",
    "dosage",
    "dosing",
)


async def test_check_output_safety_finds_no_treatment_language(
    reduced_ef_case_id: str, persisted_ensemble: dict, physician_context: ConversationContext
) -> None:
    artifact = await generate_physician_brief(
        reduced_ef_case_id, persisted_ensemble["id"], physician_context
    )
    bundle = DecisionSupportBundle.model_validate(artifact.payload)

    scan = scan_bundle_strings(bundle)
    assert scan, "expected at least one string field to have been scanned"

    blocked = {path: decision for path, decision in scan.items() if decision.blocked}

    # Every matched term across every blocked field must be explainable by
    # the single documented pre-existing false positive (bare "clinical"
    # word-boundary match on ensemble.py's real, hardcoded methodology
    # caveat) — see physician_brief.py's "Safety scan false positives"
    # section. Anything else indicates real prescriptive/treatment language
    # slipped in, which must fail this test.
    for path, decision in blocked.items():
        assert decision.matched_terms == ["regex:\\b(clinical(ly)?)\\b"], (
            f"unexpected safety match at {path!r}: {decision.matched_terms!r} "
            f"(reason: {decision.reason})"
        )

    # Independently confirm the known match is exactly where expected: the
    # real ensemble assumption text about "clinical confidence intervals",
    # nowhere else (e.g. not in anything this module authored itself).
    for path in blocked:
        assert path.startswith("assumptions["), (
            f"pre-existing benign safety match appeared outside assumptions[]: {path!r}"
        )

    # No matched term anywhere (blocked or not — check_output_safety can
    # also surface non-fatal signal) resembles genuine treatment-
    # recommendation language.
    full_text = " ".join(
        value
        for entry in bundle.derived_evidence
        for value in entry.values()
        if isinstance(value, str)
    )
    full_text += " " + " ".join(bundle.limitations)
    full_text += " " + " ".join(bundle.assumptions)
    if bundle.question:
        full_text += " " + bundle.question
    lowered = full_text.lower()
    for signal in _TREATMENT_SIGNAL_SUBSTRINGS:
        assert signal not in lowered, f"found treatment-signal substring {signal!r} in brief text"


async def test_authored_strings_pass_check_output_safety_cleanly(
    reduced_ef_case_id: str, physician_context: ConversationContext
) -> None:
    """The strings this module itself authors (question, limitations) must
    pass check_output_safety with zero exceptions — no pre-existing-false-
    positive carve-out applies to content this module controls."""
    from python.hearttwin.assistant.safety_validator import check_output_safety

    artifact = await generate_physician_brief(reduced_ef_case_id, None, physician_context)
    bundle = DecisionSupportBundle.model_validate(artifact.payload)

    assert check_output_safety(bundle.question or "").blocked is False
    for text in bundle.limitations:
        assert check_output_safety(text).blocked is False, text


# ---------------------------------------------------------------------------
# (e) missing_evidence / conflicts / possible_interpretations are empty
#     lists, not None, not fabricated, regardless of ensemble presence.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("with_ensemble", [True, False])
async def test_undetectable_fields_are_empty_lists_not_none(
    with_ensemble: bool,
    reduced_ef_case_id: str,
    persisted_ensemble: dict,
    physician_context: ConversationContext,
) -> None:
    ensemble_id = persisted_ensemble["id"] if with_ensemble else None
    artifact = await generate_physician_brief(reduced_ef_case_id, ensemble_id, physician_context)
    bundle = DecisionSupportBundle.model_validate(artifact.payload)

    assert bundle.missing_evidence == []
    assert bundle.conflicts == []
    assert bundle.possible_interpretations == []
    assert bundle.observed_evidence == []  # see design note: no tool exposes true "observed" data yet


# ---------------------------------------------------------------------------
# generate_physician_brief works with no ConversationContext at all
# ---------------------------------------------------------------------------


async def test_generate_physician_brief_works_without_context(reduced_ef_case_id: str) -> None:
    artifact = await generate_physician_brief(reduced_ef_case_id, None, None)

    assert artifact.type is AssistantArtifactType.PHYSICIAN_BRIEF
    assert artifact.patient_id is None
    assert artifact.conversation_id  # non-empty fallback, required field on AssistantArtifact
