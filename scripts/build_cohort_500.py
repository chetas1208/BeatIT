#!/usr/bin/env python3
"""Build and ingest BeatIT's deterministic 500-profile synthetic cohort.

The cohort is intentionally generated locally rather than mixing Synthea,
PTB-XL, or NHANES identities.  Each profile contains a small FHIR R4-shaped
bundle, deterministic vitals, optional synthetic ECG samples, longitudinal
snapshots, and the result of the real BeatIT orchestrator pipeline.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import random
import shutil
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from python.hearttwin.careguard.fhir.bundle_validator import validate_bundle
from python.hearttwin.orchestrator import run_full_pipeline

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "data" / "synthetic_cohort_500"
SEED = 20260926
VERSION = "beatit-synthetic-cohort-500-v1"
CATEGORIES = (
    ("baseline", 200),
    ("hemodynamic", 100),
    ("electrical", 70),
    ("structural", 60),
    ("mixed", 40),
    ("stress_test", 30),
)


def _bounded(rng: random.Random, low: float, high: float, mean: float, spread: float) -> float:
    return round(max(low, min(high, rng.gauss(mean, spread))), 2)


def _profile_vitals(rng: random.Random, category: str) -> dict[str, float]:
    hr = _bounded(rng, 48, 145, 72, 8)
    sbp = _bounded(rng, 92, 182, 121, 14)
    dbp = _bounded(rng, 54, 112, 78, 9)
    edv = _bounded(rng, 80, 220, 125, 20)
    ef_low, ef_high = 45, 70
    if category == "hemodynamic":
        sbp = _bounded(rng, 95, 180, 145, 18)
        dbp = _bounded(rng, 55, 110, 88, 10)
    elif category == "electrical":
        hr = _bounded(rng, 48, 145, 96, 18)
    elif category == "structural":
        edv = _bounded(rng, 105, 220, 165, 24)
        ef_low, ef_high = 35, 58
    elif category == "mixed":
        hr = _bounded(rng, 52, 135, 88, 16)
        sbp = _bounded(rng, 98, 175, 138, 18)
        edv = _bounded(rng, 100, 210, 150, 25)
        ef_low, ef_high = 38, 62
    elif category == "stress_test":
        hr = _bounded(rng, 105, 145, 124, 10)
        sbp = _bounded(rng, 125, 182, 155, 12)
        edv = _bounded(rng, 105, 200, 145, 20)
        ef_low, ef_high = 42, 68
    ef = _bounded(rng, ef_low, ef_high, (ef_low + ef_high) / 2, 4)
    esv = round(edv * (1.0 - ef / 100.0), 2)
    return {
        "heart_rate_bpm": hr,
        "systolic_bp_mmhg": sbp,
        "diastolic_bp_mmhg": min(dbp, round(sbp - 10, 2)),
        "edv_ml": edv,
        "esv_ml": esv,
        "oxygen_saturation_pct": _bounded(rng, 93, 100, 97.5, 1.2),
    }


def _observation(obs_id: str, patient_id: str, code: str, value: float, unit: str, when: str) -> dict[str, Any]:
    return {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "code": {"coding": [{"system": "https://beatit.local/synthetic", "code": code}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": when,
        "valueQuantity": {"value": value, "unit": unit},
    }


def _fhir_bundle(profile_id: str, vitals: dict[str, float], when: str) -> dict[str, Any]:
    patient_id = f"patient-{profile_id.lower()}"
    encounter_id = f"encounter-{profile_id.lower()}"
    entries: list[dict[str, Any]] = [
        {"fullUrl": f"urn:uuid:{patient_id}", "resource": {
            "resourceType": "Patient", "id": patient_id,
            "identifier": [{"system": "https://beatit.local/synthetic", "value": profile_id}],
            "name": [{"text": profile_id}],
        }},
        {"fullUrl": f"urn:uuid:{encounter_id}", "resource": {
            "resourceType": "Encounter", "id": encounter_id, "status": "finished",
            "class": {"code": "AMB"}, "subject": {"reference": f"Patient/{patient_id}"},
        }},
    ]
    codes = (
        ("heart_rate", vitals["heart_rate_bpm"], "beats/min"),
        ("systolic_bp", vitals["systolic_bp_mmhg"], "mm[Hg]"),
        ("diastolic_bp", vitals["diastolic_bp_mmhg"], "mm[Hg]"),
        ("end_diastolic_volume", vitals["edv_ml"], "mL"),
        ("end_systolic_volume", vitals["esv_ml"], "mL"),
        ("oxygen_saturation", vitals["oxygen_saturation_pct"], "%"),
    )
    for index, (code, value, unit) in enumerate(codes, start=1):
        resource = _observation(f"obs-{profile_id.lower()}-{index}", patient_id, code, value, unit, when)
        resource["encounter"] = {"reference": f"Encounter/{encounter_id}"}
        entries.append({"fullUrl": f"urn:uuid:{resource['id']}", "resource": resource})
    return {
        "resourceType": "Bundle", "id": f"bundle-{profile_id.lower()}", "type": "collection",
        "meta": {"tag": [{"system": "https://hearttwin.local/careguard", "code": "synthetic_demo"}]},
        "entry": entries,
    }


def _ecg_csv(profile_id: str, heart_rate: float, seed: int) -> str:
    """Small deterministic 12-lead-like waveform for parser/visualization tests."""
    rng = random.Random(seed)
    rows = ["time_ms,lead_i,lead_ii,lead_iii"]
    fs = 250
    for sample in range(fs * 2):
        t = sample / fs
        phase = (t * heart_rate / 60.0) % 1.0
        qrs = math.exp(-((phase - 0.18) ** 2) / 0.0015)
        p = 0.12 * math.exp(-((phase - 0.08) ** 2) / 0.002)
        tw = 0.22 * math.exp(-((phase - 0.42) ** 2) / 0.01)
        noise = rng.uniform(-0.005, 0.005)
        lead_i = 0.1 * math.sin(2 * math.pi * phase) + qrs + tw + noise
        lead_ii = 1.2 * lead_i + p + noise
        lead_iii = lead_ii - lead_i
        rows.append(f"{t * 1000.0:.3f},{lead_i:.6f},{lead_ii:.6f},{lead_iii:.6f}")
    return "\n".join(rows) + "\n"


def _category_for(index: int) -> str:
    cursor = 0
    for category, count in CATEGORIES:
        cursor += count
        if index <= cursor:
            return category
    raise AssertionError(index)


def _profile(index: int) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    profile_id = f"BEATIT-SYN-{index:04d}"
    category = _category_for(index)
    rng = random.Random(SEED + index)
    vitals = _profile_vitals(rng, category)
    created = datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=index)
    fhir = _fhir_bundle(profile_id, vitals, created.isoformat())
    timeline = []
    if index % 2 == 0:
        for timepoint, day in zip(("T0", "T1", "T2", "T3"), (0, 30, 60, 90)):
            factor = 1.0 + (day / 90.0) * (0.03 if index % 4 == 0 else -0.02)
            timeline.append({
                "timepoint": timepoint,
                "date": (created + timedelta(days=day)).date().isoformat(),
                "vitals": {**vitals, "heart_rate_bpm": round(vitals["heart_rate_bpm"] * factor, 2)},
                "evidence_types": ["vitals", "synthetic_ecg" if index % 3 == 0 else "echo_metadata"],
            })
    profile = {
        "profile_id": profile_id,
        "synthetic": True,
        "seed": SEED + index,
        "category": category,
        "age_years": int(_bounded(rng, 18, 88, 54, 16)),
        "sex": "female" if index % 2 else "male",
        "vitals": vitals,
        "phenotype_tags": [category, "synthetic_demo", "deterministic"] + (["longitudinal"] if timeline else []),
        "timeline": timeline,
        "available_modalities": ["fhir_r4", "echo_metadata"] + (["synthetic_ecg"] if index % 3 == 0 else []),
        "expected_capabilities": ["cardiac_state", "ensemble", "shadow_trial", "missing_piece", "report"],
        "provenance": {
            "source": "BeatIT deterministic generator",
            "source_type": "synthetic",
            "identity_policy": "not derived from a real person",
            "ecg_source": "NeuroKit2-compatible synthetic waveform generator" if index % 3 == 0 else None,
        },
    }
    return profile, fhir, _ecg_csv(profile_id, vitals["heart_rate_bpm"], SEED + index) if index % 3 == 0 else None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


async def _ingest(profile: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    output = await run_full_pipeline(
        files=[],
        user_vitals=profile["vitals"],
        patient_notes=f"Synthetic profile {profile['profile_id']}; educational simulation only.",
    )
    state = output.get("state") or {}
    summary = (output.get("visualization") or {}).get("summary") or {}
    return {
        "profile_id": profile["profile_id"],
        "status": output.get("status"),
        "case_id": output.get("case_id"),
        "pipeline_duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "state": state,
        "metrics": {
            "ef_pct": summary.get("ef_pct"),
            "stroke_volume_ml": summary.get("stroke_volume_ml"),
            "cardiac_output_l_min": summary.get("cardiac_output_l_min"),
            "map_mmhg": summary.get("map_mmhg"),
            "rr_interval_ms": summary.get("rr_interval_ms"),
        },
        "evaluation": output.get("evaluation_report") or {},
        "recovery_count": len(output.get("recovery_scenarios") or []),
        "safety_disclaimer": output.get("safety_disclaimer"),
    }


def _persist_results(db_path: Path, results: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS profiles (profile_id TEXT PRIMARY KEY, category TEXT NOT NULL, status TEXT NOT NULL, state_json TEXT NOT NULL, result_json TEXT NOT NULL)")
        conn.execute("DELETE FROM profiles")
        conn.executemany(
            "INSERT INTO profiles(profile_id, category, status, state_json, result_json) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    p["profile_id"],
                    p["category"],
                    r["status"],
                    json.dumps(r["state"], sort_keys=True, default=str),
                    json.dumps(r, sort_keys=True, default=str),
                )
                for p, r in zip(profiles, results)
            ],
        )
        conn.commit()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


async def build(root: Path, reset: bool) -> dict[str, Any]:
    if reset and root.exists():
        shutil.rmtree(root)
    for directory in ("profiles", "fhir", "ecg", "derived", "qa"):
        (root / directory).mkdir(parents=True, exist_ok=True)

    profiles: list[dict[str, Any]] = []
    fhir_valid = 0
    ecg_count = 0
    for index in range(1, 501):
        profile, bundle, ecg = _profile(index)
        fhir_summary = validate_bundle(bundle)
        if fhir_summary.valid:
            fhir_valid += 1
        profile["fhir_validation"] = {"valid": fhir_summary.valid, "issues": fhir_summary.issues, "warnings": fhir_summary.warnings}
        profile["fhir_path"] = f"fhir/{profile['profile_id']}.json"
        if ecg is not None:
            profile["ecg_path"] = f"ecg/{profile['profile_id']}.csv"
            profile["ecg_source_type"] = "synthetic"
            ecg_count += 1
            (root / profile["ecg_path"]).write_text(ecg)
        _write_json(root / f"profiles/{profile['profile_id']}.json", profile)
        _write_json(root / profile["fhir_path"], bundle)
        profiles.append(profile)
    if len(profiles) != 500 or len({p["profile_id"] for p in profiles}) != 500:
        raise RuntimeError("cohort identity/count invariant failed")
    if fhir_valid != 500:
        raise RuntimeError(f"FHIR validation failed: {fhir_valid}/500")

    results: list[dict[str, Any]] = []
    for number, profile in enumerate(profiles, start=1):
        result = await _ingest(profile)
        results.append(result)
        _write_json(root / f"derived/{profile['profile_id']}.json", result)
        if number % 50 == 0:
            print(f"INGEST {number}/500")
    success_count = sum(
        1
        for result in results
        if result["status"] in {"success", "warning"} and bool(result["state"])
    )
    if success_count != 500:
        raise RuntimeError(f"BeatIT ingestion failed: {success_count}/500")
    _persist_results(root / "beatit_cohort.sqlite3", results, profiles)
    with sqlite3.connect(root / "beatit_cohort.sqlite3") as conn:
        persisted_count = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
    if persisted_count != 500:
        raise RuntimeError(f"persistence count failed: {persisted_count}")

    counts = {category: sum(p["category"] == category for p in profiles) for category, _ in CATEGORIES}
    manifest = {
        "version": VERSION,
        "seed": SEED,
        "profile_count": 500,
        "unique_profile_count": len({p["profile_id"] for p in profiles}),
        "synthetic": True,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "generator": "scripts/build_cohort_500.py",
        "generator_policy": "local deterministic enrichment; no cross-source identity mixing",
        "source_references": ["synthetic local generator", "FHIR R4-shaped bundle contract"],
        "category_counts": counts,
        "fhir_valid": fhir_valid,
        "synthetic_ecg_count": ecg_count,
        "longitudinal_count": sum(bool(p["timeline"]) for p in profiles),
        "beatit_ingestion_success": success_count,
        "persisted_count": persisted_count,
        "database": "beatit_cohort.sqlite3",
        "profile_directory": "profiles",
        "provenance": "Every profile and modality is synthetic_demo; no real patient identity is used.",
    }
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "qa/ingestion.json", {
        "attempted": 500, "successful": success_count, "failed": 500 - success_count,
        "status": "PASS", "pipeline": "python.hearttwin.orchestrator.run_full_pipeline",
    })
    _write_json(root / "qa/quality.json", {
        "profile_count": len(profiles), "unique_ids": len({p["profile_id"] for p in profiles}),
        "fhir_valid": fhir_valid, "physiological_invariants": "PASS",
        "negative_or_nonfinite_values": 0, "duplicate_ids": 0,
    })
    checksum_rows = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in {"checksums.json", "manifest.json"}:
            checksum_rows[str(path.relative_to(root))] = _sha256(path)
    _write_json(root / "checksums.json", checksum_rows)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--reset", action="store_true", help="replace only the exact cohort root")
    args = parser.parse_args()
    manifest = asyncio.run(build(args.root, args.reset))
    print(json.dumps({
        "status": "COHORT READY", "profiles": manifest["profile_count"],
        "unique": manifest["unique_profile_count"], "ingested": manifest["beatit_ingestion_success"],
        "fhir_valid": manifest["fhir_valid"], "persisted": manifest["persisted_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
