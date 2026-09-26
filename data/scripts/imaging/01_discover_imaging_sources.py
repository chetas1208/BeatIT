#!/usr/bin/env python3
"""Imaging stage 01 — discover approved CT sources and record their REAL access
status. Writes data/imaging_source_manifest.{json,csv} (spec §9).

No pixel data is downloaded here; ingestion is gated by 02 on recorded license +
access status. Controlled sources (MultiD4CAD, ImageCAS, TCIA, RAD-ChestCT) stay
access_pending unless their access/DUA/license flags are set AND files are local.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_01_sources")
    log.info("=== Imaging 01: discover imaging sources ===")

    entries = []
    for sid, s in I.SOURCES.items():
        st = I.source_access_state(sid)
        if st["access_verified"]:
            access_type = "local" if st["local_present"] else s["access_type"]
        elif s["access_type"] == "controlled" or s["dua_required"]:
            access_type = "controlled"
        else:
            access_type = s["access_type"]
        entries.append({
            "source_id": s["source_id"], "source_name": s["source_name"],
            "version": st["version"] or "", "doi": s["doi"], "license": s["license"],
            "access_type": access_type, "access_verified": st["access_verified"],
            "dua_required": s["dua_required"], "dua_recorded": st["dua_recorded"],
            "image_modality": s["image_modality"], "image_formats": s["image_formats"],
            "has_same_subject_clinical_data": s["has_same_subject_clinical_data"],
            "has_reference_masks": s["has_reference_masks"],
            "clinical_metadata_fields": s["clinical_metadata_fields"],
            "subject_id_field": s["subject_id_field"], "study_id_field": s["study_id_field"],
            "series_id_field": s["series_id_field"],
            "downloaded_at": None, "local_root": st["root"], "checksum_manifest": None,
            "local_present": st["local_present"], "tier": s["tier"],
            "expected_max_cases": s["expected_max_cases"],
            "approved_uses": s["approved_uses"], "prohibited_uses": s["prohibited_uses"],
            "access_state": ("access_verified" if st["access_verified"]
                             else "access_pending" if s["access_type"] != "open"
                             else "enabled_open"),
        })

    I.C.write_json(I.IMAGING_SOURCE_MANIFEST_JSON,
                   {"generated_at": I.C.now_iso(), "sources": entries})
    cols = ["source_id", "source_name", "version", "doi", "license", "access_type",
            "access_verified", "dua_required", "dua_recorded", "has_same_subject_clinical_data",
            "has_reference_masks", "local_present", "tier", "expected_max_cases", "access_state"]
    with open(I.IMAGING_SOURCE_MANIFEST_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(entries)

    for e in entries:
        log.info("%-16s access=%-16s verified=%s masks=%s", e["source_id"],
                 e["access_state"], e["access_verified"], e["has_reference_masks"])
    log.info("=== Imaging 01 complete: %d sources ===", len(entries))
    print(f"sources={len(entries)}")


if __name__ == "__main__":
    main()
