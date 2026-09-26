"""Focused tests for the versioned M8 evidence taxonomy."""

from __future__ import annotations

from python.hearttwin.missing_piece.evidence import (
    EDUCATIONAL_SCOPE,
    EVIDENCE_MAP_VERSION,
    EVIDENCE_TAXONOMY,
    EVIDENCE_TAXONOMY_VERSION,
    evidence_constraints,
    evidence_taxonomy,
)


def test_taxonomy_is_explicit_versioned_and_deterministically_ordered() -> None:
    assert EVIDENCE_MAP_VERSION == "m8-evidence-map-v1"
    assert EVIDENCE_TAXONOMY_VERSION == "m8-evidence-taxonomy-v1"
    assert evidence_taxonomy() == EVIDENCE_TAXONOMY
    assert [item.evidence_type for item in EVIDENCE_TAXONOMY] == [
        "echocardiographic_measurement",
        "blood_pressure_series",
        "repeat_ecg",
    ]
    assert all(item.source.startswith(EVIDENCE_TAXONOMY_VERSION) for item in EVIDENCE_TAXONOMY)


def test_constraints_are_rebuilt_without_mutable_state_leaking() -> None:
    first = evidence_constraints()
    second = evidence_constraints()

    assert first == second
    assert first is not second
    assert first[0].constrained_parameters is not second[0].constrained_parameters

    first[0].constrained_parameters.append("temporary_proxy")
    assert "temporary_proxy" not in second[0].constrained_parameters


def test_taxonomy_is_educational_only_and_uses_no_care_labels() -> None:
    assert EDUCATIONAL_SCOPE == "Educational simulation proxy mapping only."
    text = " ".join(
        f"{item.label} {item.rationale} {item.source}" for item in EVIDENCE_TAXONOMY
    ).lower()
    assert "diagnos" not in text
    assert "treat" not in text
    assert "prescrib" not in text
