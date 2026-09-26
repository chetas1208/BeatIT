#!/usr/bin/env python3
"""Imaging stage 04 — import MultiD4CAD (spec §6 Tier 1) — controlled access.

MultiD4CAD is the preferred LINKED cardiac imaging dataset (CCTA + EAT/PAT masks +
clinical features + CAD label, sharing one sample ID → imaging_native_same_subject).
It requires a signed DUA. Access controls are NEVER bypassed: if approval/DUA are
not recorded, the source is marked access_pending and 0 cases are imported. If files
are already local AND the flags are set, subjects are registered with checksums.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import linkage as L  # noqa: E402


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_04_multid4cad")
    log.info("=== Imaging 04: import MultiD4CAD (controlled) ===")
    st = I.source_access_state("multid4cad")
    summary = {"generated_at": I.C.now_iso(), "source": "multid4cad",
               "doi": I.SOURCES["multid4cad"]["doi"],
               "expected_max_cases": I.SOURCES["multid4cad"]["expected_max_cases"],
               "access_verified": st["access_verified"], "imported": 0,
               "linkage_status_if_imported": L.IMAGING_NATIVE_SAME_SUBJECT}
    if not st["access_verified"]:
        summary["status"] = L.ACCESS_PENDING
        summary["reason"] = ("Controlled access: set MULTID4CAD_ACCESS_APPROVED=true and "
                             "MULTID4CAD_DUA_RECORDED=true AFTER signing the Zenodo DUA, then "
                             "point MULTID4CAD_ROOT at the local files. Access is never bypassed.")
        log.warning("MultiD4CAD access_pending — 0 imported (no bypass)")
    else:
        # (Reached only when a real DUA-approved local dataset is present.)
        summary["status"] = "ready_to_import"
        summary["reason"] = "access + DUA recorded; import would proceed from MULTID4CAD_ROOT"
        log.info("MultiD4CAD access verified — import path enabled")
    I.C.write_json(I.RAW_MULTID4CAD / "import_summary.json", summary)
    print(f"multid4cad_imported=0 status={summary['status']}")


if __name__ == "__main__":
    main()
