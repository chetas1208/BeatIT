"""Focused M8 orchestration tests."""

from __future__ import annotations

from copy import deepcopy

from python.hearttwin.ensemble import run_ensemble
from python.hearttwin.missing_piece.engine import (
    run_missing_piece,
    run_missing_piece_shadow_effect,
)
from python.hearttwin.shadow_trial_contracts import (
    ScenarioDefinition,
    ScenarioParameterChange,
)
from python.hearttwin.tests.test_ensemble import _request, _state


def _ensemble() -> dict:
    return run_ensemble(
        _request(
            _state(
                {
                    "heart_rate_bpm": 88.0,
                    "systolic_bp_mmhg": 135.0,
                    "diastolic_bp_mmhg": 85.0,
                    "edv_ml": 130.0,
                    "esv_ml": 70.0,
                }
            ),
            seed=91,
            sample_count=8,
        )
    )


def test_missing_piece_is_deterministic_target_specific_and_non_mutating() -> None:
    ensemble = _ensemble()
    before = deepcopy(ensemble)

    first = run_missing_piece(ensemble, "stroke_volume_ml")
    second = run_missing_piece(ensemble, "stroke_volume_ml")

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert ensemble == before
    assert first.target_metric == "stroke_volume_ml"
    assert first.sensitivities
    assert all(item.method == "finite_difference" for item in first.sensitivities)
    assert all(item.metric_id == first.target_metric for item in first.sensitivities)
    assert all(item.method == "evidence-priority-score-v1" for item in first.evidence_ranking)


def test_missing_piece_ranks_declared_evidence_without_claiming_completeness() -> None:
    result = run_missing_piece(_ensemble(), "cardiac_output_l_min")

    assert result.evidence_ranking
    assert result.evidence_ranking[0].ranking_score >= result.evidence_ranking[-1].ranking_score
    assert result.completeness["complete"] is False
    assert "medical recommendation" in " ".join(result.limitations)


def test_shadow_effect_missing_piece_keeps_fixed_scenario_target() -> None:
    ensemble = _ensemble()
    scenario = ScenarioDefinition(
        id="afterload-120",
        label="Fixed afterload hypothetical",
        origin_snapshot_id=ensemble["origin_snapshot_id"],
        parameters=[ScenarioParameterChange(parameter="afterload_index", value=1.2)],
    )
    result = run_missing_piece_shadow_effect(
        ensemble,
        scenario,
        "stroke_volume_ml",
        shadow_trial_id="trial-1",
    )
    assert result.provenance.source == "shadow_trial"
    assert result.sensitivity_availability["target_kind"] == "shadow_effect"
    assert result.sensitivities
    assert all(item.target_kind == "shadow_effect" for item in result.sensitivities)
    assert "causal" in " ".join(result.limitations).lower()
