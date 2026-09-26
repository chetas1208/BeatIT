#!/usr/bin/env python3
"""Imaging stage 02 — verify imaging licenses/access and gate ingestion (spec §9).

Ingestion of a source is permitted only when its license/access is recorded. This
stage records, per source, whether ingestion may proceed and why, and computes
checksums for any locally-present pixel files. Writes
analysis/imaging/license_verification.csv and updates the source manifest.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402


def local_files(sid: str) -> list[Path]:
    roots = {"totalsegmentator": I.RAW_TOTALSEG, "multid4cad": I.RAW_MULTID4CAD,
             "imagecas": I.RAW_IMAGECAS, "tcia": I.RAW_TCIA, "rad-chestct": I.RAW_RADCHEST}
    r = roots.get(sid)
    if not r or not r.exists():
        return []
    return [p for p in r.rglob("*") if p.is_file() and p.suffix.lower() in
            (".gz", ".nii", ".dcm", ".nrrd", ".mha", ".mhd", ".npz", ".zip")]


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_02_licenses")
    log.info("=== Imaging 02: verify imaging licenses + gate ingestion ===")

    rows = []
    checksums = {}
    for sid, s in I.SOURCES.items():
        st = I.source_access_state(sid)
        files = local_files(sid)
        # checksum any local pixel files (bounded)
        for p in files[:200]:
            try:
                checksums[str(p.relative_to(I.C.DATA_DIR))] = I.C.sha256_file(p)
            except Exception:
                pass
        can_ingest = st["access_verified"]
        if s["access_type"] == "open":
            reason = "open license; ingestion permitted" if can_ingest else "source disabled"
        elif can_ingest:
            reason = "access + DUA/license recorded; ingestion permitted"
        else:
            missing = []
            if not st["access_approved"]:
                missing.append(s["access_flag_env"])
            if s["dua_required"] and not st["dua_recorded"]:
                missing.append(s["dua_flag_env"])
            reason = ("access_pending — controlled source; not approved. "
                      f"Set {', '.join(missing)} after signing the DUA. "
                      "Access controls are NEVER bypassed.")
        rows.append({"source_id": sid, "access_type": s["access_type"],
                     "license": s["license"], "access_verified": st["access_verified"],
                     "dua_required": s["dua_required"], "dua_recorded": st["dua_recorded"],
                     "local_files": len(files), "can_ingest": can_ingest, "reason": reason})
        log.info("%-16s can_ingest=%s (%s)", sid, can_ingest, reason[:60])

    with open(I.ANALYSIS_IMAGING / "license_verification.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    if checksums:
        I.C.write_json(I.ANALYSIS_IMAGING / "imaging_file_checksums.json", checksums)

    # annotate source manifest with checksum-manifest path + can_ingest
    if I.IMAGING_SOURCE_MANIFEST_JSON.exists():
        man = I.C.read_json(I.IMAGING_SOURCE_MANIFEST_JSON)
        gate = {r["source_id"]: r["can_ingest"] for r in rows}
        for e in man.get("sources", []):
            e["can_ingest"] = gate.get(e["source_id"], False)
            if checksums:
                e["checksum_manifest"] = "analysis/imaging/imaging_file_checksums.json"
        I.C.write_json(I.IMAGING_SOURCE_MANIFEST_JSON, man)

    n_ingest = sum(1 for r in rows if r["can_ingest"])
    log.info("=== Imaging 02 complete: %d/%d sources ingestible; %d local files hashed ===",
             n_ingest, len(rows), len(checksums))
    print(f"ingestible={n_ingest}/{len(rows)}")


if __name__ == "__main__":
    main()
