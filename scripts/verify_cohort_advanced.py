#!/usr/bin/env python3
"""Exercise 100 diverse cohort states through ensemble/trial/missing-piece math."""

from __future__ import annotations

import json
from pathlib import Path

from python.hearttwin.ensemble import EnsembleDistributionRequest, EnsembleRequest, run_ensemble
from python.hearttwin.missing_piece.engine import run_missing_piece
from python.hearttwin.schemas import CardiacTwinState
from python.hearttwin.shadow_trial_contracts import ScenarioDefinition, ScenarioParameterChange
from python.hearttwin.shadow_trial_engine import run_shadow_trial

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "data" / "synthetic_cohort_500"
SAMPLE_INDICES = (
    list(range(1, 21))
    + list(range(201, 221))
    + list(range(301, 321))
    + list(range(371, 391))
    + list(range(431, 451))
    + list(range(471, 491))
)


def _value(state: CardiacTwinState, section: str, name: str, default: float) -> float:
    measured = getattr(getattr(state, section), name, None)
    return float(getattr(measured, "value", default))


def _request(state: CardiacTwinState, seed: int) -> EnsembleRequest:
    distributions = [
        ("heart_rate_bpm", _value(state, "measurements", "heart_rate_bpm", 72), 30.0, 200.0),
        ("preload_index", _value(state, "hemodynamics", "preload_index", 1.0), 0.0, 1.5),
        ("afterload_index", _value(state, "hemodynamics", "afterload_index", 1.0), 0.0, 2.0),
        ("contractility_index", _value(state, "hemodynamics", "contractility_index", 1.0), 0.0, 1.5),
        ("systemic_vascular_resistance_index", _value(state, "hemodynamics", "systemic_vascular_resistance_index", 1.0), 0.0, 2.0),
    ]
    configs = [EnsembleDistributionRequest(
        parameter_id=parameter,
        family="fixed",
        parameters={"value": max(low, min(high, value))},
        bounds={"min": low, "max": high},
        source="measurement" if parameter == "heart_rate_bpm" else "derived",
        rationale="Synthetic cohort deterministic validation; not a clinical distribution.",
        version="cohort-500-validation-v1",
        evidence_ids=[f"{state.case_id}.synthetic"],
    ) for parameter, value, low, high in distributions]
    return EnsembleRequest(
        origin_snapshot_id=state.case_id,
        state=state,
        seed=seed,
        sample_count=3,
        distributions=configs,
        origin_quality="synthetic",
        origin_provenance=[{"source": "synthetic_cohort_500", "source_id": state.case_id, "note": "Synthetic validation only."}],
        evidence_ids=[f"{state.case_id}.synthetic"],
    )


def main() -> int:
    categories: dict[str, int] = {}
    trial_count = 0
    missing_count = 0
    isolation_ids: set[str] = set()
    for index in SAMPLE_INDICES:
        profile_id = f"BEATIT-SYN-{index:04d}"
        profile = json.loads((COHORT / "profiles" / f"{profile_id}.json").read_text())
        derived = json.loads((COHORT / "derived" / f"{profile_id}.json").read_text())
        state = CardiacTwinState.model_validate(derived["state"])
        if state.case_id in isolation_ids:
            raise SystemExit(f"profile isolation failure: duplicate case id {state.case_id}")
        isolation_ids.add(state.case_id)
        categories[profile["category"]] = categories.get(profile["category"], 0) + 1
        ensemble = run_ensemble(_request(state, 900000 + index))
        if ensemble["accepted_sample_count"] != 3:
            raise SystemExit(f"ensemble rejected profile {profile_id}")
        trial = run_shadow_trial(
            ensemble,
            ScenarioDefinition(
                id=f"cohort-afterload-{index}",
                label="Synthetic bounded afterload scenario",
                origin_snapshot_id=state.case_id,
                parameters=[ScenarioParameterChange(parameter="afterload_index", baseline=1.0, value=1.2, delta=0.2, unit="index")],
            ),
        )
        if trial.requested_pairs != 3 or trial.valid_pairs != 3:
            raise SystemExit(f"shadow trial failed profile {profile_id}")
        trial_count += 1
        missing = run_missing_piece(ensemble, "stroke_volume_ml", available_evidence_types=["repeat_ecg", "repeat_echo"])
        if not missing.sensitivities and not missing.evidence_priority:
            raise SystemExit(f"missing piece empty for profile {profile_id}")
        missing_count += 1
    report = {
        "sample_count": len(SAMPLE_INDICES),
        "categories": categories,
        "ensemble_success": len(SAMPLE_INDICES),
        "shadow_trial_success": trial_count,
        "missing_piece_success": missing_count,
        "profile_isolation": len(isolation_ids) == len(SAMPLE_INDICES),
        "status": "PASS",
    }
    out = COHORT / "qa" / "advanced_e2e.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
