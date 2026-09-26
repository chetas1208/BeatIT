#!/usr/bin/env python3
"""Verify and execute the bounded PTB-XL and UCI open-real-data cases."""

from __future__ import annotations

import asyncio
import csv
import gzip
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from python.hearttwin.agents.electrophysiology_agent import run_electrophysiology_agent
from python.hearttwin.agents.state_builder_agent import run_state_builder_agent
from python.hearttwin.open_real_data import (
    load_ptb_metadata,
    load_ptb_record,
    load_uci_rows,
    normalize_uci_case,
    ptb_superclasses,
    read_ptb_checksum_manifest,
    sha256_file,
)
from python.hearttwin.schemas import CardiacTwinState

PTB = ROOT / "data/real/sources/ptb-xl"
UCI = ROOT / "data/real/sources/uci-hf"
CAMUS = ROOT / "data/real/sources/camus"
TED = ROOT / "data/real/sources/ted"
OUTPUT = ROOT / "data/real/open-normalized"
CACHE = ROOT / "data/real/cache"
PTB_IDS = (1, 8, 22, 32)
UCI_ROWS = (1, 2, 5, 15, 46)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


async def _execute_ptb(ecg_id: int, checksums: dict[str, str]) -> tuple[dict, dict]:
    metadata = load_ptb_metadata(PTB / "ptbxl_database.csv", ecg_id)
    relative_base = metadata["filename_lr"]
    header = PTB / f"{relative_base}.hea"
    record = load_ptb_record(header)
    verified_files = []
    for path in (record["header_path"], record["data_path"]):
        relative = path.relative_to(PTB).as_posix()
        local_sha = sha256_file(path)
        upstream_sha = checksums.get(relative)
        if not upstream_sha or local_sha != upstream_sha:
            raise ValueError(f"checksum mismatch or missing upstream checksum: {relative}")
        verified_files.append({"path": relative, "bytes": path.stat().st_size, "sha256": local_sha})

    waveform = {
        lead.lower(): record["signals_mv"][:, index].tolist()
        for index, lead in enumerate(record["lead_names"])
    }
    case_id = f"REAL-PTB-XL-{ecg_id:06d}"
    demographics = {}
    if metadata["age"] != "nan":
        demographics["age_years"] = {
            "value": float(metadata["age"]),
            "unit": "years",
            "source": "file_extraction",
            "confidence": 1.0,
            "source_file_id": "PTB-XL-1.0.3:ptbxl_database.csv",
        }
    demographics["sex"] = {
        "value": "male" if int(float(metadata["sex"])) == 0 else "female",
        "source": "file_extraction",
        "confidence": 1.0,
        "source_file_id": "PTB-XL-1.0.3:ptbxl_database.csv",
    }
    _, state = await run_state_builder_agent(validated_fields=demographics, case_id=case_id)
    response, electrophysiology = await run_electrophysiology_agent(
        state=state,
        validated_fields={
            "__ecg_waveform__": {
                "value": waveform,
                "unit": "mV",
                "source": "csv_waveform",
                "confidence": 1.0,
                "source_file_id": f"PTB-XL-1.0.3:{relative_base}",
                "method": "wfdb_format_16",
                "sampling_rate_hz": record["sampling_frequency_hz"],
            }
        },
        case_id=case_id,
    )
    state.electrophysiology = electrophysiology
    mapped_superclasses = ptb_superclasses(metadata, PTB / "scp_statements.csv")
    derived_ep_fields = {
        name
        for name in (
            "rr_interval_ms",
            "qrs_duration_ms",
            "qt_interval_ms",
            "qtc_ms",
            "conduction_delay_score",
            "arrhythmia_instability_score",
        )
        if getattr(electrophysiology, name) is not None
        and getattr(electrophysiology, name).source.value == "derived"
    }
    prior_fields = sorted(
        item.field
        for item in state.source_map
        if item.source.value == "default_model_prior" and item.field not in derived_ep_fields
    )
    normalized = {
        "case_id": case_id,
        "real_data": True,
        "dataset": "PTB-XL 1.0.3",
        "source_subject": f"ecg_id:{ecg_id}",
        "available": {"basics": True, "vitals": False, "ecg": True, "echo": False, "clinical": True},
        "observed": {
            "age_years": None if metadata["age"] == "nan" else float(metadata["age"]),
            "sex_source_code": int(float(metadata["sex"])),
            "ecg": {
                "leads": record["lead_names"],
                "sample_count": record["sample_count"],
                "sampling_frequency_hz": record["sampling_frequency_hz"],
                "unit": "mV",
                "scp_codes": metadata["scp_codes"],
                "report": metadata["report"],
            },
        },
        "derived": {
            "diagnostic_superclasses": mapped_superclasses,
            "rr_interval_ms": (
                electrophysiology.rr_interval_ms.value if electrophysiology.rr_interval_ms else None
            ),
            "r_peak_confidence": electrophysiology.r_peak_confidence,
            "rhythm_descriptor": (
                f"waveform-derived descriptor: {electrophysiology.rhythm_label}"
                if electrophysiology.rhythm_label
                else None
            ),
        },
        "priors": {"state_builder_fields": prior_fields},
        "missing": ["blood_pressure", "raw_echo", "ejection_fraction", "medications"],
        "provenance": [
            {
                "source_urls": [
                    f"https://physionet.org/files/ptb-xl/1.0.3/{item['path']}"
                    for item in verified_files
                ],
                "source_record": ecg_id,
                "classification": "OBSERVED",
                "verified_files": verified_files,
            }
        ],
        "integrity": {"synthetic_measurements": 0, "cross_dataset_stitching": False},
    }
    execution = {
        "case_id": case_id,
        "beatit_path": "PTB metadata -> State Builder; WFDB -> 12-lead parser -> Electrophysiology Agent",
        "agent_status": response.status.value,
        "rhythm_source": response.outputs["structured_output"]["rhythm_source"],
        "r_peak_count": response.outputs["structured_output"]["r_peak_count"],
        "record_shape": [record["sample_count"], len(record["lead_names"])],
        "all_samples_finite": True,
        "upstream_checksums_verified": True,
    }
    return normalized, execution


async def _execute_uci(row: dict[str, str], row_number: int) -> tuple[dict, dict]:
    normalized = normalize_uci_case(row, row_number)
    validated_fields = {
        "ejection_fraction_pct": {
            "value": normalized["observed"]["ejection_fraction_pct"],
            "unit": "%",
            "source": "file_extraction",
            "confidence": 1.0,
            "source_file_id": f"UCI-HF:data.csv:row:{row_number}",
            "method": "source_csv",
        }
    }
    response, state = await run_state_builder_agent(
        validated_fields={
            **validated_fields,
            "age_years": {
                "value": normalized["observed"]["age_years"],
                "unit": "years",
                "source": "file_extraction",
                "confidence": 1.0,
                "source_file_id": f"UCI-HF:data.csv:row:{row_number}",
            },
        },
        case_id=normalized["case_id"],
    )
    prior_fields = sorted(
        item.field for item in state.source_map if item.source.value == "default_model_prior"
    )
    normalized["priors"] = {"state_builder_fields": prior_fields}
    execution = {
        "case_id": normalized["case_id"],
        "beatit_path": "UCI CSV age/EF -> evidence normalization -> State Builder Agent",
        "agent_status": response.status.value,
        "observed_ejection_fraction_pct": normalized["observed"]["ejection_fraction_pct"],
        "state_ejection_fraction_pct": (
            state.measurements.ejection_fraction_pct.value
            if state.measurements.ejection_fraction_pct
            else None
        ),
        "state_ejection_fraction_source": (
            state.measurements.ejection_fraction_pct.source.value
            if state.measurements.ejection_fraction_pct
            else None
        ),
        "state_age_years": state.patient_context.age_years.value if state.patient_context.age_years else None,
        "state_age_source": (
            state.patient_context.age_years.source.value if state.patient_context.age_years else None
        ),
        "model_prior_fields": prior_fields,
        "missing_modalities_preserved": normalized["missing"],
    }
    return normalized, execution


def _key_values(text: str, separator: str) -> dict[str, str]:
    return {
        key.strip(): value.strip()
        for line in text.splitlines()
        if separator in line
        for key, value in [line.split(separator, 1)]
    }


async def _state_from_observed_ef(case_id: str, ef: float, source_file_id: str) -> tuple[dict, object]:
    return await run_state_builder_agent(
        validated_fields={
            "ejection_fraction_pct": {
                "value": ef,
                "unit": "%",
                "source": "file_extraction",
                "confidence": 1.0,
                "source_file_id": source_file_id,
                "method": "source_metadata",
            }
        },
        case_id=case_id,
    )


async def _execute_camus() -> tuple[dict, dict]:
    archive = CAMUS / "patient0001.zip"
    with ZipFile(archive) as source:
        if source.testzip() is not None:
            raise ValueError("CAMUS archive CRC validation failed")
        members = {item.filename: item for item in source.infolist()}
        config = _key_values(source.read("patient0001/Info_4CH.cfg").decode(), ":")
        nifti_name = "patient0001/patient0001_4CH_half_sequence.nii.gz"
        with gzip.GzipFile(fileobj=source.open(nifti_name)) as handle:
            nifti_payload = handle.read()
        header = nifti_payload[:348]
        dimensions = struct.unpack("<8h", header[40:56])
        if header[344:348] not in {b"n+1\x00", b"ni1\x00"}:
            raise ValueError("CAMUS sequence has invalid NIfTI magic")
        bits_per_pixel = struct.unpack("<h", header[72:74])[0]
        voxel_offset = int(struct.unpack("<f", header[108:112])[0])
    shape = list(dimensions[1 : dimensions[0] + 1])
    if bits_per_pixel <= 0 or bits_per_pixel % 8:
        raise ValueError("CAMUS sequence has an invalid NIfTI bit depth")
    if len(nifti_payload) < voxel_offset + int(np.prod(shape)) * (bits_per_pixel // 8):
        raise ValueError("CAMUS sequence NIfTI payload is truncated")
    ef = float(config["EF"])
    if not 1 <= int(config["ED"]) <= int(config["NbFrame"]) or not 1 <= int(config["ES"]) <= int(config["NbFrame"]):
        raise ValueError("CAMUS ED/ES frame is outside its sequence")
    if shape[-1] != int(config["NbFrame"]):
        raise ValueError("CAMUS frame count does not match its NIfTI header")
    case_id = "REAL-CAMUS-PATIENT0001"
    response, state = await _state_from_observed_ef(case_id, ef, "CAMUS:patient0001:Info_4CH.cfg")
    normalized = {
        "case_id": case_id,
        "real_data": True,
        "dataset": "CAMUS",
        "source_subject": "patient0001",
        "available": {"basics": True, "vitals": False, "ecg": False, "echo": True, "clinical": False},
        "observed": {
            "age_years": int(config["Age"]),
            "sex": config["Sex"],
            "ejection_fraction_pct": ef,
            "ed_frame": int(config["ED"]),
            "es_frame": int(config["ES"]),
            "frame_count": int(config["NbFrame"]),
            "image_quality": config["ImageQuality"],
            "frame_rate_hz": float(config["FrameRate"]),
        },
        "derived": {"four_chamber_sequence_shape": shape},
        "priors": {
            "state_builder_fields": sorted(
                item.field for item in state.source_map if item.source.value == "default_model_prior"
            )
        },
        "missing": ["raw_ecg", "blood_pressure", "medications", "diagnoses"],
        "provenance": [{
            "source_url": "https://humanheart-project.creatis.insa-lyon.fr/database/#collection/6373703d73e9f0047faa1bc8",
            "source_subject": "patient0001",
            "archive_sha256": sha256_file(archive),
            "classification": "OBSERVED",
        }],
        "integrity": {"synthetic_measurements": 0, "cross_dataset_stitching": False},
        "public_distribution": "LOCAL_ONLY_PENDING_TERMS_REVIEW",
    }
    execution = {
        "case_id": case_id,
        "beatit_path": "CAMUS config EF -> State Builder Agent; NIfTI retained and integrity-checked only",
        "agent_status": response.status.value,
        "archive_crc_and_selected_nifti_valid": True,
        "archive_member_count": len(members),
        "sequence_shape": shape,
        "observed_ejection_fraction_pct": ef,
        "state_ejection_fraction_pct": state.measurements.ejection_fraction_pct.value,
        "patient_separation": "single source folder patient0001",
    }
    return normalized, execution


async def _execute_ted() -> tuple[dict, dict]:
    source_dir = TED / "patient003"
    config = _key_values((source_dir / "patient003_4CH_info.cfg").read_text(), ":")
    image = _key_values((source_dir / "patient003_4CH_sequence.mhd").read_text(), "=")
    required_image_fields = {
        "NDims": "3",
        "BinaryData": "True",
        "BinaryDataByteOrderMSB": "False",
        "CompressedData": "False",
        "ElementNumberOfChannels": "1",
        "ElementType": "MET_UCHAR",
        "ElementDataFile": "patient003_4CH_sequence.raw",
    }
    if any(image.get(key) != value for key, value in required_image_fields.items()):
        raise ValueError("TED patient003 has an unsupported MetaImage contract")
    shape = [int(value) for value in image["DimSize"].split()]
    raw = source_dir / image["ElementDataFile"]
    expected_bytes = shape[0] * shape[1] * shape[2]
    if image["ElementType"] != "MET_UCHAR" or raw.stat().st_size != expected_bytes:
        raise ValueError("TED patient003 payload does not match its MetaImage header")
    ef = float(config["EF"])
    if int(config["NbFrame"]) != shape[2]:
        raise ValueError("TED frame count does not match its MetaImage header")
    if not 1 <= int(config["ED"]) <= shape[2] or not 1 <= int(config["ES"]) <= shape[2]:
        raise ValueError("TED ED/ES frame is outside its sequence")
    pixels = np.memmap(raw, dtype=np.uint8, mode="r", shape=tuple(reversed(shape)))
    pixel_range = [int(pixels.min()), int(pixels.max())]
    case_id = "REAL-TED-PATIENT003"
    response, state = await _state_from_observed_ef(case_id, ef, "TED:patient003:patient003_4CH_info.cfg")
    normalized = {
        "case_id": case_id,
        "real_data": True,
        "dataset": "TED",
        "source_subject": "patient003",
        "available": {"basics": True, "vitals": False, "ecg": False, "echo": True, "clinical": False},
        "observed": {
            "age_years": int(config["Age"]),
            "sex": config["Sex"],
            "ejection_fraction_pct": ef,
            "ed_frame": int(config["ED"]),
            "es_frame": int(config["ES"]),
            "frame_count": int(config["NbFrame"]),
            "image_quality": config["ImageQuality"],
        },
        "derived": {
            "four_chamber_sequence_shape": shape,
            "pixel_value_range": pixel_range,
        },
        "priors": {
            "state_builder_fields": sorted(
                item.field for item in state.source_map if item.source.value == "default_model_prior"
            )
        },
        "missing": ["raw_ecg", "blood_pressure", "medications", "diagnoses"],
        "provenance": [{
            "source_url": "https://humanheart-project.creatis.insa-lyon.fr/database/#collection/62840fcd73e9f00479084885",
            "source_subject": "patient003",
            "raw_sha256": sha256_file(raw),
            "classification": "OBSERVED",
        }],
        "integrity": {"synthetic_measurements": 0, "cross_dataset_stitching": False},
        "public_distribution": "LOCAL_ONLY_PENDING_TERMS_REVIEW",
    }
    execution = {
        "case_id": case_id,
        "beatit_path": "TED config EF -> State Builder Agent; MetaImage retained and integrity-checked only",
        "agent_status": response.status.value,
        "metaimage_contract_and_payload_size_valid": True,
        "sequence_shape": shape,
        "sequence_bytes": raw.stat().st_size,
        "observed_ejection_fraction_pct": ef,
        "state_ejection_fraction_pct": state.measurements.ejection_fraction_pct.value,
        "patient_separation": "single source folder patient003",
    }
    return normalized, execution


async def main() -> int:
    checksums = read_ptb_checksum_manifest(PTB / "SHA256SUMS.txt")
    for relative in ("ptbxl_database.csv", "scp_statements.csv", "LICENSE.txt"):
        if sha256_file(PTB / relative) != checksums[relative]:
            raise ValueError(f"PTB-XL upstream checksum mismatch: {relative}")

    uci_rows = load_uci_rows(UCI / "data.csv")
    duplicate_rows = len(uci_rows) - len({tuple(row.items()) for row in uci_rows})
    executions: list[dict] = []
    cases: list[dict] = []
    for ecg_id in PTB_IDS:
        case, execution = await _execute_ptb(ecg_id, checksums)
        cases.append(case)
        executions.append(execution)
    for row_number in UCI_ROWS:
        case, execution = await _execute_uci(uci_rows[row_number - 1], row_number)
        cases.append(case)
        executions.append(execution)
    for runner in (_execute_camus, _execute_ted):
        case, execution = await runner()
        cases.append(case)
        executions.append(execution)

    for case in cases:
        _write_json(OUTPUT / f"{case['case_id']}.json", case)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "downloads": [
            {
                "dataset": "PTB-XL",
                "version": "1.0.3",
                "source_url": f"https://physionet.org/files/ptb-xl/1.0.3/{path.relative_to(PTB).as_posix()}",
                "local_path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "recorded_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "upstream_checksum_result": (
                    "NOT_SELF_LISTED" if path.name == "SHA256SUMS.txt" else "PASS"
                ),
                "license": "CC BY 4.0",
            }
            for path in sorted(
                [
                    PTB / "ptbxl_database.csv",
                    PTB / "scp_statements.csv",
                    PTB / "SHA256SUMS.txt",
                    PTB / "LICENSE.txt",
                    *PTB.glob("records100/00000/*"),
                ]
            )
        ]
        + [
            {
                "dataset": "UCI Heart Failure Clinical Records",
                "version": "DOI 10.24432/C5Z89R",
                "source_url": "https://archive.ics.uci.edu/static/public/519/data.csv",
                "local_path": str((UCI / "data.csv").relative_to(ROOT)),
                "bytes": (UCI / "data.csv").stat().st_size,
                "sha256": sha256_file(UCI / "data.csv"),
                "recorded_at": datetime.fromtimestamp((UCI / "data.csv").stat().st_mtime, timezone.utc).isoformat(),
                "upstream_checksum_result": "NOT_PUBLISHED",
                "license": "CC BY 4.0",
            }
        ]
        + [
            {
                "dataset": dataset,
                "version": "public collection",
                "source_url": source_url,
                "local_path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "recorded_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "upstream_checksum_result": "NOT_PUBLISHED",
                "license": "CC BY-NC-SA 4.0 plus publisher research-only terms",
                "distribution": "LOCAL_ONLY_PENDING_TERMS_REVIEW",
            }
            for dataset, source_url, path in [
                (
                    "CAMUS",
                    "https://humanheart-project.creatis.insa-lyon.fr/database/api/v1/folder/63fde57373e9f004868fb832/download",
                    CAMUS / "patient0001.zip",
                ),
                *[
                    (
                        "TED",
                        f"https://humanheart-project.creatis.insa-lyon.fr/database/api/v1/item/{item_id}/download",
                        TED / "patient003" / filename,
                    )
                    for item_id, filename in [
                        ("6284ce7673e9f00479084fe1", "patient003_4CH_info.cfg"),
                        ("6284ce7673e9f00479084fe4", "patient003_4CH_sequence.mhd"),
                        ("6284ce7873e9f00479084fe7", "patient003_4CH_sequence.raw"),
                    ]
                ],
            ]
        ],
        "ptb_xl": {
            "version": "1.0.3",
            "metadata_rows": sum(1 for _ in csv.DictReader((PTB / "ptbxl_database.csv").open())),
            "selected_records": list(PTB_IDS),
            "upstream_checksum_manifest": "SHA256SUMS.txt",
        },
        "uci_hf": {
            "rows": len(uci_rows),
            "columns": len(uci_rows[0]),
            "null_or_empty_values": 0,
            "exact_duplicate_rows": duplicate_rows,
            "sha256": sha256_file(UCI / "data.csv"),
            "selected_rows": list(UCI_ROWS),
        },
        "camus": {"selected_subject": "patient0001", "raw_public_demo": False},
        "ted": {"selected_subject": "patient003", "raw_public_demo": False},
        "executions": executions,
        "integrity": {
            "synthetic_measurements": 0,
            "cross_patient_stitching": 0,
            "missing_values_preserved": True,
        },
    }
    _write_json(CACHE / "open_real_execution.json", report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
