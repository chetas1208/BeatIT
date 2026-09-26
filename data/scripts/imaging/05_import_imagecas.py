#!/usr/bin/env python3
"""Imaging stage 05 — import ImageCAS (spec §6 Tier 3) — controlled request.

~1000 coronary CTA scans + coronary-artery annotations. Used for imaging_only
benchmarking (never attached to an eICU patient; no invented meds/labs). Requires
a recorded license/request; access is never bypassed. If the license flag is not
set, the source is access_pending and 0 cases are imported.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import linkage as L  # noqa: E402


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_05_imagecas")
    log.info("=== Imaging 05: import ImageCAS (controlled) ===")
    st = I.source_access_state("imagecas")
    summary = {"generated_at": I.C.now_iso(), "source": "imagecas",
               "expected_max_cases": I.SOURCES["imagecas"]["expected_max_cases"],
               "access_verified": st["access_verified"], "imported": 0,
               "linkage_status_if_imported": L.IMAGING_ONLY,
               "coronary_dice_note": "coronary Dice only if the endpoint declares a coronary target "
                                     "(current VISTA deployment does not)."}
    if not st["access_verified"]:
        summary["status"] = L.ACCESS_PENDING
        summary["reason"] = ("Set IMAGECAS_LICENSE_RECORDED=true and IMAGECAS_ROOT after the "
                             "ImageCAS data request is approved. Access is never bypassed.")
        log.warning("ImageCAS access_pending — 0 imported (no bypass)")
    else:
        summary["status"] = "ready_to_import"
        summary["reason"] = "license recorded; import would proceed as imaging_only from IMAGECAS_ROOT"
    I.C.write_json(I.RAW_IMAGECAS / "import_summary.json", summary)
    print(f"imagecas_imported=0 status={summary['status']}")


if __name__ == "__main__":
    main()
