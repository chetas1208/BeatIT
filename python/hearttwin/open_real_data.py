"""Load bounded, single-subject open datasets without filling missing modalities."""

from __future__ import annotations

import ast
import csv
import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np

PTB_LEADS = ("I", "II", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6")
MAX_PTB_SAMPLES = 1_000_000
MAX_CHECKSUM_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_METADATA_BYTES = 32 * 1024 * 1024
MAX_UCI_BYTES = 1024 * 1024
MAX_SCP_CODES_LENGTH = 16 * 1024
UCI_COLUMNS = (
    "age",
    "anaemia",
    "creatinine_phosphokinase",
    "diabetes",
    "ejection_fraction",
    "high_blood_pressure",
    "platelets",
    "serum_creatinine",
    "serum_sodium",
    "sex",
    "smoking",
    "time",
    "death_event",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_ptb_checksum_manifest(path: Path) -> dict[str, str]:
    if path.stat().st_size > MAX_CHECKSUM_MANIFEST_BYTES:
        raise ValueError(f"{path}: checksum manifest is too large")
    checksums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            checksum, relative_path = line.split(maxsplit=1)
        except ValueError as exc:
            raise ValueError(f"{path}: malformed checksum line") from exc
        relative_path = relative_path.lstrip("*")
        if len(checksum) != 64 or any(character not in "0123456789abcdefABCDEF" for character in checksum):
            raise ValueError(f"{path}: malformed SHA-256 for {relative_path}")
        if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
            raise ValueError(f"{path}: unsafe checksum path {relative_path}")
        if relative_path in checksums:
            raise ValueError(f"{path}: duplicate checksum path {relative_path}")
        checksums[relative_path] = checksum.lower()
    return checksums


def load_ptb_record(header_path: Path) -> dict[str, Any]:
    """Read the PTB-XL 16-bit, multiplexed WFDB record described by ``header_path``."""
    if header_path.stat().st_size > 64 * 1024:
        raise ValueError(f"{header_path}: WFDB header is too large")
    lines = header_path.read_text(encoding="utf-8").splitlines()
    if not lines or len(lines[0].split()) < 4:
        raise ValueError(f"{header_path}: malformed WFDB header")
    record_name, lead_count_text, frequency_text, sample_count_text = lines[0].split()[:4]
    lead_count = int(lead_count_text)
    frequency_hz = float(frequency_text)
    sample_count = int(sample_count_text)
    if not math.isfinite(frequency_hz) or frequency_hz <= 0:
        raise ValueError(f"{header_path}: sampling frequency must be positive and finite")
    if not 0 < sample_count <= MAX_PTB_SAMPLES:
        raise ValueError(f"{header_path}: unsupported sample count {sample_count}")
    if lead_count != 12 or len(lines) < lead_count + 1:
        raise ValueError(f"{header_path}: expected a 12-lead WFDB header")

    lead_names: list[str] = []
    gains: list[float] = []
    baselines: list[float] = []
    data_filename: str | None = None
    for line in lines[1 : lead_count + 1]:
        parts = line.split()
        if len(parts) < 3:
            raise ValueError(f"{header_path}: malformed WFDB signal row")
        if parts[1] != "16":
            raise ValueError(f"{header_path}: only WFDB format 16 is supported")
        if data_filename is None:
            data_filename = parts[0]
        elif data_filename != parts[0]:
            raise ValueError(f"{header_path}: split WFDB data files are unsupported")
        gain_and_baseline = parts[2].split("/", 1)[0]
        if "(" in gain_and_baseline:
            gain_text, baseline_text = gain_and_baseline.rstrip(")").split("(", 1)
        else:
            gain_text, baseline_text = gain_and_baseline, "0"
        gains.append(float(gain_text))
        baselines.append(float(baseline_text))
        lead_names.append(parts[-1].upper())

    if tuple(lead_names) != PTB_LEADS:
        raise ValueError(f"{header_path}: unexpected lead order {lead_names}")
    if any(not math.isfinite(value) or value == 0 for value in gains):
        raise ValueError(f"{header_path}: gains must be finite and non-zero")
    if any(not math.isfinite(value) for value in baselines):
        raise ValueError(f"{header_path}: baselines must be finite")
    data_path = header_path.with_name(data_filename or f"{record_name}.dat")
    if data_path.is_symlink() or data_path.resolve().parent != header_path.resolve().parent:
        raise ValueError(f"{header_path}: unsafe WFDB data path")
    expected_values = sample_count * lead_count
    expected_bytes = expected_values * np.dtype("<i2").itemsize
    if data_path.stat().st_size != expected_bytes:
        raise ValueError(
            f"{data_path}: expected {expected_values} samples, "
            f"found {data_path.stat().st_size // np.dtype('<i2').itemsize}"
        )
    raw = np.fromfile(data_path, dtype="<i2")
    if raw.size != expected_values:
        raise ValueError(f"{data_path}: expected {expected_values} samples, found {raw.size}")
    signals_mv = (raw.reshape(sample_count, lead_count) - np.asarray(baselines)) / np.asarray(gains)
    if not np.isfinite(signals_mv).all():
        raise ValueError(f"{data_path}: non-finite waveform samples")
    return {
        "record_name": record_name,
        "sampling_frequency_hz": frequency_hz,
        "sample_count": sample_count,
        "lead_names": lead_names,
        "signals_mv": signals_mv,
        "header_path": header_path,
        "data_path": data_path,
    }


def load_ptb_metadata(database_path: Path, ecg_id: int) -> dict[str, str]:
    if database_path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError(f"{database_path}: metadata file is too large")
    with database_path.open(newline="", encoding="utf-8") as handle:
        row = next((item for item in csv.DictReader(handle) if int(item["ecg_id"]) == ecg_id), None)
    if row is None:
        raise ValueError(f"PTB-XL ecg_id {ecg_id} is absent from {database_path}")
    return row


def ptb_superclasses(metadata: dict[str, str], statements_path: Path) -> list[str]:
    if statements_path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError(f"{statements_path}: statement file is too large")
    with statements_path.open(newline="", encoding="utf-8") as handle:
        classes = {
            row[""]: row["diagnostic_class"]
            for row in csv.DictReader(handle)
            if row.get("diagnostic") == "1.0"
        }
    encoded_codes = metadata["scp_codes"]
    if len(encoded_codes) > MAX_SCP_CODES_LENGTH:
        raise ValueError("PTB-XL scp_codes value is too large")
    codes = ast.literal_eval(encoded_codes)
    if not isinstance(codes, dict) or any(not isinstance(code, str) for code in codes):
        raise ValueError("PTB-XL scp_codes must be a string-keyed mapping")
    return sorted({classes[code] for code in codes if classes.get(code)})


def load_uci_rows(csv_path: Path) -> list[dict[str, str]]:
    if csv_path.stat().st_size > MAX_UCI_BYTES:
        raise ValueError(f"{csv_path}: UCI CSV is too large")
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != UCI_COLUMNS:
            raise ValueError(f"{csv_path}: unexpected UCI schema")
        rows = list(reader)
    if len(rows) != 299:
        raise ValueError(f"{csv_path}: expected 299 rows, found {len(rows)}")
    if any(None in row for row in rows):
        raise ValueError(f"{csv_path}: surplus CSV values are not allowed")
    if any(any(value == "" for value in row.values()) for row in rows):
        raise ValueError(f"{csv_path}: empty values are not allowed")
    row_values = [tuple(row[column] for column in UCI_COLUMNS) for row in rows]
    if len(set(row_values)) != len(row_values):
        raise ValueError(f"{csv_path}: duplicate rows are not allowed")
    binary_fields = ("anaemia", "diabetes", "high_blood_pressure", "sex", "smoking", "death_event")
    nonnegative_fields = (
        "age",
        "creatinine_phosphokinase",
        "ejection_fraction",
        "platelets",
        "serum_creatinine",
        "serum_sodium",
        "time",
    )
    for row_number, row in enumerate(rows, start=1):
        try:
            numeric = {field: float(row[field]) for field in nonnegative_fields}
        except ValueError as exc:
            raise ValueError(f"{csv_path}: non-numeric value at row {row_number}") from exc
        if any(not math.isfinite(value) or value < 0 for value in numeric.values()):
            raise ValueError(f"{csv_path}: invalid numeric value at row {row_number}")
        if not 0 <= numeric["ejection_fraction"] <= 100:
            raise ValueError(f"{csv_path}: invalid ejection fraction at row {row_number}")
        if numeric["age"] <= 0 or numeric["serum_sodium"] <= 0:
            raise ValueError(f"{csv_path}: invalid positive measurement at row {row_number}")
        if any(row[field] not in {"0", "1"} for field in binary_fields):
            raise ValueError(f"{csv_path}: invalid binary value at row {row_number}")
    return rows


def normalize_uci_case(row: dict[str, str], row_number: int) -> dict[str, Any]:
    observed = {
        "age_years": float(row["age"]),
        "anaemia": bool(int(row["anaemia"])),
        "creatinine_phosphokinase_mcg_l": float(row["creatinine_phosphokinase"]),
        "diabetes": bool(int(row["diabetes"])),
        "ejection_fraction_pct": float(row["ejection_fraction"]),
        "high_blood_pressure": bool(int(row["high_blood_pressure"])),
        "platelets_kiloplatelets_ml": float(row["platelets"]),
        "serum_creatinine_mg_dl": float(row["serum_creatinine"]),
        "serum_sodium_meq_l": float(row["serum_sodium"]),
        "sex_source_code": int(row["sex"]),
        "smoking": bool(int(row["smoking"])),
        "follow_up_days": int(row["time"]),
        "death_event": bool(int(row["death_event"])),
    }
    return {
        "case_id": f"REAL-UCI-HF-ROW-{row_number:03d}",
        "real_data": True,
        "dataset": "UCI Heart Failure Clinical Records",
        "source_subject": f"dataset-row-{row_number}",
        "available": {"basics": True, "vitals": False, "ecg": False, "echo": False, "clinical": True},
        "observed": observed,
        "derived": {},
        "priors": {},
        "missing": ["raw_ecg", "raw_echo", "blood_pressure", "medications"],
        "provenance": [
            {
                "source_url": "https://archive.ics.uci.edu/static/public/519/data.csv",
                "source_row": row_number,
                "classification": "OBSERVED",
            }
        ],
        "integrity": {"synthetic_measurements": 0, "cross_dataset_stitching": False},
    }
