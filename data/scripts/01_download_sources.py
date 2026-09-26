#!/usr/bin/env python3
"""Stage 01 — download all source data from official PhysioNet/GitHub roots.

Idempotent + resumable: existing complete files are skipped; interrupted files
resume via HTTP range. Writes data/source_manifest.json.

MIMIC-IV demo is fetched as a SEPARATE validation cohort and is never mixed into
the eICU main cohort. Synthea is cloned lazily only if the cohort stage requests
a synthetic fallback (handled in 04); this stage only records its metadata.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402


def eicu_plan(cfg) -> list[dict]:
    s = cfg["sources"]["eicu"]
    root = s["root"]
    return [
        {"source": "eicu", "url": s["sqlite_url"],
         "dest": C.RAW_EICU / "eicu_v2_0_1.sqlite3.gz", "min_bytes": 1_000_000},
        {"source": "eicu", "url": root + "LICENSE.txt", "dest": C.RAW_EICU / "LICENSE.txt"},
        {"source": "eicu", "url": s["checksums_url"], "dest": C.RAW_EICU / "SHA256SUMS.txt"},
    ]


def ptbxl_plan(cfg) -> list[dict]:
    s = cfg["sources"]["ptbxl"]
    return [
        {"source": "ptbxl", "url": s["metadata_csv"], "dest": C.RAW_PTBXL / "ptbxl_database.csv",
         "min_bytes": 100_000},
        {"source": "ptbxl", "url": s["scp_csv"], "dest": C.RAW_PTBXL / "scp_statements.csv"},
        {"source": "ptbxl", "url": s["license_url"], "dest": C.RAW_PTBXL / "LICENSE.txt"},
        {"source": "ptbxl", "url": s["checksums_url"], "dest": C.RAW_PTBXL / "SHA256SUMS.txt"},
    ]


def mimic_plan(cfg) -> list[dict]:
    """Best-effort validation-cohort tables. 404s are non-fatal."""
    root = cfg["sources"]["mimic"]["root"]
    files = [
        "LICENSE.txt", "SHA256SUMS.txt",
        "core/patients.csv.gz", "core/admissions.csv.gz",
        "hosp/diagnoses_icd.csv.gz", "hosp/d_icd_diagnoses.csv.gz",
    ]
    plan = []
    for f in files:
        dest = C.RAW_MIMIC / f
        plan.append({"source": "mimic", "url": root + f, "dest": dest, "optional": True})
    return plan


def main() -> None:
    C.ensure_dirs()
    log = C.get_logger("01_download_sources")
    cfg = C.load_config()
    log.info("=== Stage 01: downloading sources ===")

    manifest = []
    for entry in (eicu_plan(cfg) + ptbxl_plan(cfg) + mimic_plan(cfg)):
        src = entry["source"]
        srccfg = cfg["sources"][src]
        try:
            frag = C.download(entry["url"], entry["dest"], logger=log,
                              expect_min_bytes=entry.get("min_bytes", 1))
        except Exception as e:
            if entry.get("optional"):
                log.warning("optional file unavailable (%s): %s", entry["url"], e)
                continue
            raise
        frag.update({
            "source_name": srccfg["name"],
            "source_version": srccfg.get("version", ""),
            "official_url": entry["url"],
            "license": srccfg["license"],
            "citation": srccfg["citation"],
        })
        manifest.append(frag)

    # Record Synthea metadata without cloning (clone happens in 04 if needed).
    syn = cfg["sources"]["synthea"]
    manifest.append({
        "source_name": syn["name"], "official_url": syn["repo"], "license": syn["license"],
        "role": syn["role"], "downloaded_at": None,
        "note": "Cloned on demand only if a synthetic fallback is required.",
    })

    C.write_json(C.SOURCE_MANIFEST, {
        "generated_at": C.now_iso(),
        "mapping_rule_version": cfg["mapping_rule_version"],
        "entries": manifest,
    })
    log.info("=== Stage 01 complete: %d files in manifest ===", len(manifest))


if __name__ == "__main__":
    main()
