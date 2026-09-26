"""Golden vectors for the canonical backend probabilistic evaluator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from python.hearttwin.ensemble import EnsembleRequest, _evaluate, run_ensemble


GOLDEN_DIR = Path(__file__).parents[3] / "fixtures" / "golden" / "probabilistic"
ENSEMBLE_FIXTURES = (
    "fixed-only.json",
    "normal-basic.json",
    "bounded-rejection.json",
    "mixed-distributions.json",
    "synthetic-replay.json",
    "scenario-compatible.json",
)


def test_fixed_afterload_golden_vector() -> None:
    fixture_path = GOLDEN_DIR / "fixed-afterload.json"
    fixture = json.loads(fixture_path.read_text())
    assert fixture["version"] == "m5.5-golden-v1"

    result = _evaluate(fixture["base"], fixture["parameters"])

    for key, expected in fixture["expected"].items():
        assert result[key] == expected


def _canonical_fixture_projection(result: dict) -> dict:
    return {
        "accepted_sample_count": result["accepted_sample_count"],
        "rejected_sample_count": result["rejected_sample_count"],
        "samples": [
            {
                key: sample[key]
                for key in ("id", "index", "parameters", "outputs", "valid", "rejection_reasons")
            }
            for sample in result["samples"]
        ],
        "distributions": result["distributions"],
        "representative_sample_ids": result["representative_sample_ids"],
        "provenance": result["provenance"],
    }


def _normalize_fixture_identity(projection: dict) -> dict:
    """Keep numerical golden vectors independent of the versioned ID scheme."""
    normalized = {**projection}
    normalized["samples"] = [
        {**sample, "id": f"sample-{sample['index']}"}
        for sample in projection["samples"]
    ]
    normalized["representative_sample_ids"] = {
        label: f"sample-{sample_id.rsplit('-', 1)[-1]}"
        for label, sample_id in projection["representative_sample_ids"].items()
    }
    return normalized


@pytest.mark.parametrize("fixture_name", ENSEMBLE_FIXTURES)
def test_canonical_ensemble_golden_vectors(fixture_name: str) -> None:
    fixture = json.loads((GOLDEN_DIR / fixture_name).read_text())
    request = EnsembleRequest.model_validate(fixture["input"])

    assert fixture["engine_version"] == request.physiology_version
    assert fixture["tolerances"] == {"mode": "exact", "absolute": 0.0, "relative": 0.0}

    result = run_ensemble(request)

    assert _normalize_fixture_identity(_canonical_fixture_projection(result)) == _normalize_fixture_identity(fixture["expected"])
    assert run_ensemble(request) == result


def test_bounded_rejection_golden_vector_keeps_rejection_reasons() -> None:
    fixture = json.loads((GOLDEN_DIR / "bounded-rejection.json").read_text())
    result = run_ensemble(EnsembleRequest.model_validate(fixture["input"]))

    rejected = [sample for sample in result["samples"] if not sample["valid"]]
    assert result["rejected_sample_count"] == len(rejected) > 0
    assert all(
        sample["rejection_reasons"] == ["heart_rate_bpm: sampled value outside declared bounds"]
        for sample in rejected
    )


def test_lineage_golden_vectors_preserve_synthetic_and_scenario_metadata() -> None:
    synthetic = json.loads((GOLDEN_DIR / "synthetic-replay.json").read_text())
    synthetic_result = run_ensemble(EnsembleRequest.model_validate(synthetic["input"]))
    assert synthetic_result["provenance"]["origin_quality"] == "synthetic"
    assert synthetic_result["provenance"]["origin_provenance"][0]["source"] == "synthetic_replay"

    scenario = json.loads((GOLDEN_DIR / "scenario-compatible.json").read_text())
    scenario_result = run_ensemble(EnsembleRequest.model_validate(scenario["input"]))
    assert scenario_result["provenance"]["parent_scenario_id"] == "m4-load-reduction-golden"
