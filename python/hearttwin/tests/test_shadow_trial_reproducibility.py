"""Reproducibility and persistence checks for the M6 Shadow Trial engine."""

from __future__ import annotations

import json
from copy import deepcopy

from python.hearttwin.ensemble import run_ensemble
from python.hearttwin.shadow_trial_contracts import (
    ScenarioDefinition,
    ScenarioParameterChange,
    ShadowTrialResult,
)
from python.hearttwin.shadow_trial_engine import run_shadow_trial
from python.hearttwin.storage.shadow_trial_store import SQLiteShadowTrialStore
from python.hearttwin.tests.test_ensemble import _request, _state


def _ensemble(baseline_vitals: dict, *, sample_count: int = 4) -> dict:
    return run_ensemble(_request(_state(baseline_vitals), seed=137, sample_count=sample_count))


def _scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        id="reproducibility-afterload",
        label="Reproducibility afterload hypothetical",
        parameters=[
            ScenarioParameterChange(
                parameter="afterload_index",
                value=1.2,
                unit="index",
            ),
        ],
    )


def test_same_input_has_same_trial_id_fingerprint_and_payload(baseline_vitals) -> None:  # type: ignore[no-untyped-def]
    ensemble = _ensemble(baseline_vitals)
    scenario = _scenario()

    first = run_shadow_trial(ensemble, scenario)
    second = run_shadow_trial(ensemble, scenario)

    assert first.id == second.id
    assert first.fingerprint == second.fingerprint
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_reversed_baseline_sample_order_preserves_trial_identity(baseline_vitals) -> None:  # type: ignore[no-untyped-def]
    ensemble = _ensemble(baseline_vitals)
    reversed_ensemble = {**ensemble, "samples": list(reversed(ensemble["samples"]))}

    first = run_shadow_trial(ensemble, _scenario())
    reversed_result = run_shadow_trial(reversed_ensemble, _scenario())

    assert first.id == reversed_result.id
    assert first.fingerprint == reversed_result.fingerprint
    assert first.model_dump(mode="json") == reversed_result.model_dump(mode="json")


def test_running_trial_does_not_mutate_baseline_ensemble(baseline_vitals) -> None:  # type: ignore[no-untyped-def]
    ensemble = _ensemble(baseline_vitals)
    before = deepcopy(ensemble)

    run_shadow_trial(ensemble, _scenario())

    assert ensemble == before


def test_parameter_declaration_order_is_not_part_of_trial_identity(baseline_vitals) -> None:  # type: ignore[no-untyped-def]
    ensemble = _ensemble(baseline_vitals)
    first = ScenarioDefinition(
        id="ordered-scenario",
        label="Ordered scenario",
        parameters=[
            ScenarioParameterChange(parameter="afterload_index", value=1.2, unit="index"),
            ScenarioParameterChange(parameter="preload_index", value=1.1, unit="index"),
        ],
    )
    second = first.model_copy(update={"parameters": list(reversed(first.parameters))})

    first_result = run_shadow_trial(ensemble, first)
    second_result = run_shadow_trial(ensemble, second)

    assert first_result.id == second_result.id
    assert first_result.model_dump(mode="json") == second_result.model_dump(mode="json")


def test_persisted_result_round_trips_through_canonical_json(tmp_path, baseline_vitals) -> None:  # type: ignore[no-untyped-def]
    result = run_shadow_trial(_ensemble(baseline_vitals), _scenario())
    payload = result.model_dump(mode="json")
    database = tmp_path / "shadow-trials.sqlite3"

    SQLiteShadowTrialStore(database).save(result.id, payload)
    persisted = SQLiteShadowTrialStore(database).get(result.id)

    assert persisted is not None
    assert json.loads(json.dumps(persisted, sort_keys=True)) == payload
    restored = ShadowTrialResult.model_validate(persisted)
    assert restored.model_dump(mode="json") == payload
