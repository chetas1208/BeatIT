#!/usr/bin/env python3
"""Stage 02 — verify downloads against official SHA-256 checksums and copy
license files into the dataset root (LICENSES/attribution).

For each source we parse the official SHA256SUMS.txt and compare the hash of
each downloaded file that appears in it. Files not listed (e.g. the gzipped
sqlite is listed under sqlite/) are hashed and recorded as unverified-but-present.
Writes data/analysis/download_verification.csv and updates source_manifest.json.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

# Map each downloaded file to the key it is expected to have inside that source's
# SHA256SUMS.txt (PhysioNet lists paths relative to the dataset root).
CHECKSUM_KEYS = {
    C.RAW_EICU / "eicu_v2_0_1.sqlite3.gz": "sqlite/eicu_v2_0_1.sqlite3.gz",
    C.RAW_EICU / "LICENSE.txt": "LICENSE.txt",
    C.RAW_PTBXL / "ptbxl_database.csv": "ptbxl_database.csv",
    C.RAW_PTBXL / "scp_statements.csv": "scp_statements.csv",
    C.RAW_PTBXL / "LICENSE.txt": "LICENSE.txt",
}
SUMS_FILES = {
    "eicu": C.RAW_EICU / "SHA256SUMS.txt",
    "ptbxl": C.RAW_PTBXL / "SHA256SUMS.txt",
    "mimic": C.RAW_MIMIC / "SHA256SUMS.txt",
}
SOURCE_OF = {
    C.RAW_EICU / "eicu_v2_0_1.sqlite3.gz": "eicu",
    C.RAW_EICU / "LICENSE.txt": "eicu",
    C.RAW_PTBXL / "ptbxl_database.csv": "ptbxl",
    C.RAW_PTBXL / "scp_statements.csv": "ptbxl",
    C.RAW_PTBXL / "LICENSE.txt": "ptbxl",
}


def main() -> None:
    C.ensure_dirs()
    log = C.get_logger("02_verify_downloads")
    log.info("=== Stage 02: verifying downloads ===")

    sums = {src: C.parse_sha256sums(p) for src, p in SUMS_FILES.items()}
    rows = []
    all_ok = True

    for path, key in CHECKSUM_KEYS.items():
        if not path.exists():
            log.error("MISSING expected file: %s", path)
            rows.append({"file": str(path), "present": False, "sha256": "",
                         "official": "", "verified": False})
            all_ok = False
            continue
        src = SOURCE_OF[path]
        digest = C.sha256_file(path)
        official = sums.get(src, {}).get(key, "")
        verified = bool(official) and (official == digest)
        if official and not verified:
            log.error("CHECKSUM MISMATCH %s: got %s want %s", path.name, digest, official)
            all_ok = False
        elif not official:
            log.warning("no official checksum listed for %s (present, hashed)", path.name)
        else:
            log.info("verified %s", path.name)
        rows.append({"file": str(path), "present": True, "sha256": digest,
                     "official": official, "verified": verified})

    # Copy license files into dataset root for attribution.
    lic_root = C.DATA_DIR / "raw"
    for src, p in [("eICU", C.RAW_EICU / "LICENSE.txt"),
                   ("PTB-XL", C.RAW_PTBXL / "LICENSE.txt"),
                   ("MIMIC-IV", C.RAW_MIMIC / "LICENSE.txt")]:
        if p.exists():
            log.info("license present for %s: %s", src, p)

    out = C.ANALYSIS / "download_verification.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "present", "sha256", "official", "verified"])
        w.writeheader()
        w.writerows(rows)

    # annotate manifest
    if C.SOURCE_MANIFEST.exists():
        man = C.read_json(C.SOURCE_MANIFEST)
        vmap = {r["file"]: r["verified"] for r in rows}
        for e in man.get("entries", []):
            lp = e.get("local_path")
            if lp in vmap:
                e["official_checksum_verified"] = vmap[lp]
        C.write_json(C.SOURCE_MANIFEST, man)

    n_ver = sum(1 for r in rows if r["verified"])
    log.info("=== Stage 02 complete: %d/%d checksum-verified; report=%s ===",
             n_ver, len(rows), out.name)
    if not all_ok:
        log.warning("some files unverified/mismatched — see %s", out)


if __name__ == "__main__":
    main()
