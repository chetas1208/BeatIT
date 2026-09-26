#!/usr/bin/env python3
"""Benchmark the deterministic ensemble engine on a synthetic fixture.

This script measures only ``run_ensemble``. Fixture loading, Pydantic model
construction, and request construction happen outside the timed region.
Results are produced only when this script is run; this file contains no
precomputed performance claims.

Usage:
    python scripts/benchmark_ensemble.py
    python scripts/benchmark_ensemble.py --warmups 2 --repeats 5 --json
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "fixtures" / "hearttwin" / "manual_baseline.json"
SAMPLE_COUNTS = (50, 100, 250, 500, 1000)

# Direct execution places only scripts/ on sys.path. Add the repository root
# so the benchmark works both as ``python scripts/...`` and from another cwd.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.hearttwin.ensemble import (
    EnsembleDistributionRequest,
    EnsembleRequest,
    run_ensemble,
)
from python.hearttwin.schemas import (
    CardiacTwinState,
    Hemodynamics,
    MeasuredValue,
    Measurements,
    ValueSource,
)


def _measured(value: float, unit: str) -> MeasuredValue:
    """Build a provenance-bearing value from the synthetic fixture."""

    return MeasuredValue(
        value=value,
        unit=unit,
        source=ValueSource.USER_INPUT,
        confidence=1.0,
        source_file_id="manual_baseline.synthetic",
    )


def _load_synthetic_state() -> CardiacTwinState:
    """Load the committed synthetic baseline fixture into the engine schema."""

    fixture = json.loads(FIXTURE_PATH.read_text())
    vitals = fixture["user_vitals"]
    return CardiacTwinState(
        case_id="benchmark-manual-baseline-synthetic",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        data_quality_score=1.0,
        measurements=Measurements(
            heart_rate_bpm=_measured(vitals["heart_rate_bpm"], "bpm"),
            systolic_bp_mmhg=_measured(vitals["systolic_bp_mmhg"], "mmHg"),
            diastolic_bp_mmhg=_measured(vitals["diastolic_bp_mmhg"], "mmHg"),
            edv_ml=_measured(vitals["edv_ml"], "mL"),
            esv_ml=_measured(vitals["esv_ml"], "mL"),
            oxygen_saturation_pct=_measured(vitals["oxygen_saturation_pct"], "%"),
        ),
        hemodynamics=Hemodynamics(
            preload_index=_measured(1.0, "index"),
            afterload_index=_measured(1.0, "index"),
            contractility_index=_measured(1.0, "index"),
            systemic_vascular_resistance_index=_measured(1.0, "index"),
        ),
        warnings=[fixture["description"]],
    )


def _normal_distribution(
    parameter_id: str,
    mean_value: float,
    standard_deviation: float,
    minimum: float,
    maximum: float,
) -> EnsembleDistributionRequest:
    return EnsembleDistributionRequest(
        parameter_id=parameter_id,
        family="normal",
        parameters={"mean": mean_value, "sd": standard_deviation},
        bounds={"min": minimum, "max": maximum},
        source="population_prior",
        evidence_ids=["manual_baseline.synthetic"],
        rationale="Synthetic benchmark prior; not a clinical distribution.",
        version="benchmark-synthetic-v1",
    )


def _build_request(state: CardiacTwinState, sample_count: int, seed: int) -> EnsembleRequest:
    """Create one valid request shared by all measured repetitions."""

    distributions = [
        _normal_distribution("heart_rate_bpm", 72.0, 4.0, 30.0, 200.0),
        _normal_distribution("preload_index", 1.0, 0.05, 0.0, 1.5),
        _normal_distribution("afterload_index", 1.0, 0.05, 0.0, 2.0),
        _normal_distribution("contractility_index", 1.0, 0.05, 0.0, 1.5),
        _normal_distribution(
            "systemic_vascular_resistance_index", 1.0, 0.05, 0.0, 2.0
        ),
    ]
    return EnsembleRequest(
        origin_snapshot_id=state.case_id,
        state=state,
        seed=seed,
        sample_count=sample_count,
        distributions=distributions,
    )


def _measure(
    state: CardiacTwinState,
    sample_count: int,
    repeats: int,
    warmups: int,
    seed: int,
) -> dict[str, Any]:
    request = _build_request(state, sample_count, seed)

    for _ in range(warmups):
        result = run_ensemble(request)
        if result["requested_sample_count"] != sample_count:
            raise RuntimeError("ensemble warmup returned an unexpected sample count")

    durations_ms: list[float] = []
    accepted_count: int | None = None
    for _ in range(repeats):
        started_ns = time.perf_counter_ns()
        result = run_ensemble(request)
        elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
        durations_ms.append(elapsed_ms)

        if result["requested_sample_count"] != sample_count:
            raise RuntimeError("ensemble run returned an unexpected sample count")
        current_accepted = result["accepted_sample_count"]
        if accepted_count is None:
            accepted_count = current_accepted
        elif current_accepted != accepted_count:
            raise RuntimeError("seeded ensemble runs were not reproducible")

    return {
        "sample_count": sample_count,
        "accepted_sample_count": accepted_count,
        "durations_ms": durations_ms,
        "min_ms": min(durations_ms),
        "median_ms": median(durations_ms),
        "mean_ms": mean(durations_ms),
        "max_ms": max(durations_ms),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--warmups",
        type=int,
        default=1,
        help="Unmeasured runs per sample count (default: 1).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Measured runs per sample count (default: 3).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260926,
        help="Seed passed to the Python ensemble engine.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the table format.",
    )
    args = parser.parse_args()
    if args.warmups < 0:
        parser.error("--warmups must be non-negative")
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    return args


def main() -> int:
    args = _parse_args()
    state = _load_synthetic_state()
    rows = [
        _measure(state, sample_count, args.repeats, args.warmups, args.seed)
        for sample_count in SAMPLE_COUNTS
    ]
    payload = {
        "benchmark": "python.hearttwin.ensemble.run_ensemble",
        "fixture": str(FIXTURE_PATH.relative_to(REPO_ROOT)),
        "synthetic_only": True,
        "seed": args.seed,
        "warmups": args.warmups,
        "repeats": args.repeats,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "results": rows,
        "limitations": [
            "Measures local wall-clock execution only; no hardware-normalized claim is made.",
            "Uses one committed synthetic baseline state and synthetic independent priors.",
            "Includes result construction and summary statistics performed by run_ensemble.",
            "Excludes fixture loading, Pydantic request construction, and process startup.",
        ],
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print("Ensemble benchmark: measured results from this invocation")
    print(f"fixture={payload['fixture']} seed={args.seed} warmups={args.warmups} repeats={args.repeats}")
    print("samples  accepted  min_ms  median_ms  mean_ms  max_ms")
    for row in rows:
        print(
            f"{row['sample_count']:>7}  {row['accepted_sample_count']:>8}  "
            f"{row['min_ms']:>6.3f}  {row['median_ms']:>9.3f}  "
            f"{row['mean_ms']:>7.3f}  {row['max_ms']:>7.3f}"
        )
    print("No performance numbers are asserted until this script is run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
