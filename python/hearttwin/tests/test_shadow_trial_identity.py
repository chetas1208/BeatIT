from __future__ import annotations

import pytest

from python.hearttwin.shadow_trial_identity import (
    DuplicateSampleIDError,
    MissingPairError,
    MissingSampleIDError,
    PairNotFoundError,
    UnexpectedPairError,
    build_pair_index,
    lookup_pair,
    make_pair_identity,
    scenario_sample_id,
)


def test_baseline_to_scenario_identity_is_stable() -> None:
    first = make_pair_identity("sample-000284")
    second = make_pair_identity("sample-000284")

    assert first == second
    assert first.sample_id == "sample-000284"
    assert first.baseline_twin_id == "sample-000284"
    assert first.scenario_twin_id == "scenario-sample-000284"
    assert scenario_sample_id("sample-000284") == "scenario-sample-000284"


@pytest.mark.parametrize("bad_id", [None, "", "   "])
def test_missing_baseline_ids_are_rejected(bad_id: object) -> None:
    with pytest.raises(MissingSampleIDError):
        scenario_sample_id(bad_id)  # type: ignore[arg-type]


def test_duplicate_baseline_ids_are_rejected() -> None:
    with pytest.raises(DuplicateSampleIDError, match="sample-1"):
        build_pair_index(["sample-1", "sample-1"])


def test_duplicate_scenario_ids_are_rejected() -> None:
    with pytest.raises(DuplicateSampleIDError, match="scenario-sample-1"):
        build_pair_index(
            ["sample-1", "sample-2"],
            ["scenario-sample-1", "scenario-sample-1"],
        )


def test_missing_and_unexpected_scenario_ids_are_rejected() -> None:
    with pytest.raises(MissingPairError, match="scenario-sample-2"):
        build_pair_index(["sample-1", "sample-2"], ["scenario-sample-1"])

    with pytest.raises(UnexpectedPairError, match="scenario-orphan"):
        build_pair_index(
            ["sample-1"],
            ["scenario-sample-1", "scenario-orphan"],
        )


def test_lookup_is_independent_of_baseline_and_scenario_order() -> None:
    baseline_ids = ["sample-1", "sample-2", "sample-3"]
    scenario_ids = [scenario_sample_id(sample_id) for sample_id in reversed(baseline_ids)]
    pair_index = build_pair_index(list(reversed(baseline_ids)), scenario_ids)

    assert lookup_pair(pair_index, "sample-1").scenario_twin_id == "scenario-sample-1"
    assert lookup_pair(pair_index, "sample-2").scenario_twin_id == "scenario-sample-2"
    assert lookup_pair(pair_index, "sample-3").scenario_twin_id == "scenario-sample-3"


def test_lookup_reports_missing_pair() -> None:
    pair_index = build_pair_index(["sample-1"])

    with pytest.raises(PairNotFoundError, match="sample-404"):
        lookup_pair(pair_index, "sample-404")
