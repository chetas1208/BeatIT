from __future__ import annotations

import json
from pathlib import Path

from python.hearttwin.ensemble import EnsembleRequest, run_ensemble
from python.hearttwin.shadow_trial_engine import ScenarioDefinition, run_shadow_trial


ROOT = Path(__file__).parents[3]


def test_m6_golden_fixture_matrix_is_present_and_synthetic() -> None:
    expected = {
        "fixed-baseline-simple-scenario.json",
        "mixed-distribution-scenario.json",
        "bounded-invalid-pairs.json",
        "zero-delta-scenario.json",
        "reproducibility-case.json",
        "synthetic-demo-case.json",
    }
    fixture_dir = ROOT / "fixtures" / "golden" / "shadow_trials"
    assert expected <= {path.name for path in fixture_dir.glob("*.json")}
    for name in expected:
        fixture = json.loads((fixture_dir / name).read_text())
        assert fixture["version"] == "m6-golden-v1"
        assert fixture["scenario"]["id"]
        assert fixture["expected"]


def test_fixed_baseline_afterload_shadow_trial_vector() -> None:
    fixture = json.loads((ROOT / "fixtures/golden/shadow_trials/fixed-baseline-afterload.json").read_text())
    baseline_path = ROOT / "fixtures/golden/probabilistic/fixed-only.json"
    baseline_fixture = json.loads(baseline_path.read_text())
    ensemble = run_ensemble(EnsembleRequest.model_validate(baseline_fixture["input"]))
    result = run_shadow_trial(ensemble, ScenarioDefinition.model_validate(fixture["scenario"]), metrics=fixture["metrics"])
    expected = fixture["expected"]
    assert result.id == expected["trial_id"]
    assert result.fingerprint == expected["fingerprint"]
    assert result.valid_pairs == expected["valid_pairs"]
    assert result.invalid_pairs == expected["invalid_pairs"]
    assert [pair.deltas for pair in result.paired_results] == expected["pair_deltas"]
    assert {item.metric_id: item.median_delta for item in result.effect_distributions} == expected["effect_medians"]
