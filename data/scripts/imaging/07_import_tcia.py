#!/usr/bin/env python3
"""Imaging stage 07 — import TCIA / RAD-ChestCT (spec §6 Tier 2/5) — restricted.

Only added to the fused cohort when an official same-subject linkage document is
present AND verified. Do not assume a TCIA collection has clinical metadata. With
no verified linkage document these remain access_pending and 0 cases are imported.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import linkage as L  # noqa: E402


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_07_tcia")
    log.info("=== Imaging 07: import TCIA / RAD-ChestCT (restricted) ===")
    out = []
    for sid in ("tcia", "rad-chestct"):
        st = I.source_access_state(sid)
        rec = {"source": sid, "access_verified": st["access_verified"], "imported": 0,
               "status": "ready_to_import" if st["access_verified"] else L.ACCESS_PENDING,
               "required": ["official same_subject linkage document", "recorded license/DUA",
                            "verified scan identifier"],
               "reason": ("enabled + verified" if st["access_verified"] else
                          f"disabled/unverified — set {I.SOURCES[sid]['enabled_env']} and provide a "
                          "verified same-subject linkage document. Never assume clinical metadata.")}
        out.append(rec)
        log.info("%s -> %s", sid, rec["status"])
    I.C.write_json(I.RAW_TCIA / "import_summary.json", {"generated_at": I.C.now_iso(), "sources": out})
    print(f"tcia_imported=0 radchest_imported=0")


if __name__ == "__main__":
    main()
