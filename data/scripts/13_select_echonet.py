#!/usr/bin/env python3
"""Stage 13 — index EchoNet-Dynamic for transparent external echo matching.

EchoNet-Dynamic is real, deidentified apical-4-chamber echocardiography video with
ejection-fraction labels. Like the PTB-XL ECG, echo is a MATCHED EXTERNAL MODALITY
(same_patient_as_ehr=false) — never claimed to be the eICU patient's own scan. The
only matching feature EchoNet exposes is EF (no age/sex), so we bucket by EF
category. Builds staging/echonet/echo_index.parquet from FileList.csv + video_index.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

RAW_ECHO = C.RAW / "echonet"
OUT = C.STAGING / "echonet"


def ef_category(ef):
    try:
        ef = float(ef)
    except (TypeError, ValueError):
        return "unknown"
    if ef < 40:
        return "reduced"       # HFrEF-range
    if ef < 50:
        return "mid"           # HFmrEF-range
    return "preserved"         # normal / HFpEF-range


HF_REPO = "miyuki17/EchoNet-Dynamic-unzipped"


def fetch_metadata(log) -> None:
    """Download FileList.csv and build the FileName->path video index (idempotent)."""
    import json
    import re
    import urllib.request
    RAW_ECHO.mkdir(parents=True, exist_ok=True)
    fl = RAW_ECHO / "FileList.csv"
    if not fl.exists():
        C.download(f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/FileList.csv",
                   fl, logger=log, retries=3, timeout=60)
    vi = RAW_ECHO / "video_index.json"
    if vi.exists():
        return
    log.info("building EchoNet video index (paginated HF tree walk)...")
    base = (f"https://huggingface.co/api/datasets/{HF_REPO}/tree/main/Videos?recursive=true")
    index, url, pages = {}, base, 0
    while url and pages < 25:
        req = urllib.request.Request(url, headers={"User-Agent": "careguard/1.0"})
        resp = urllib.request.urlopen(req, timeout=90)
        for e in json.load(resp):
            if e.get("type") == "file" and e["path"].endswith(".avi"):
                index[e["path"].split("/")[-1][:-4]] = e["path"]
        m = re.search(r'<([^>]+)>;\s*rel="next"', resp.headers.get("Link", ""))
        url = m.group(1) if m else None
        pages += 1
    C.write_json(vi, index)
    log.info("indexed %d video paths", len(index))


def main() -> None:
    import pandas as pd
    C.ensure_dirs()
    OUT.mkdir(parents=True, exist_ok=True)
    log = C.get_logger("13_select_echonet")
    log.info("=== Stage 13: index EchoNet ===")

    fetch_metadata(log)
    fl = pd.read_csv(RAW_ECHO / "FileList.csv")
    vindex = C.read_json(RAW_ECHO / "video_index.json") if (RAW_ECHO / "video_index.json").exists() else {}
    log.info("EchoNet videos=%d indexed_paths=%d", len(fl), len(vindex))

    rows = []
    for _, r in fl.iterrows():
        fn = str(r["FileName"])
        rel = vindex.get(fn)
        if not rel:
            continue
        rows.append({
            "echo_id": fn, "ef": round(float(r["EF"]), 2), "esv": round(float(r["ESV"]), 2),
            "edv": round(float(r["EDV"]), 2), "ef_category": ef_category(r["EF"]),
            "fps": float(r["FPS"]), "frames": int(r["NumberOfFrames"]),
            "height": int(r["FrameHeight"]), "width": int(r["FrameWidth"]),
            "split": r["Split"], "video_path": rel,
        })
    idx = pd.DataFrame(rows)
    idx.to_parquet(OUT / "echo_index.parquet", index=False)
    idx.to_csv(OUT / "echo_index.csv", index=False)
    dist = idx["ef_category"].value_counts().to_dict()
    C.write_json(OUT / "echo_index_summary.json", {
        "generated_at": C.now_iso(), "total": int(len(idx)),
        "ef_category_distribution": {k: int(v) for k, v in dist.items()},
        "ef_mean": round(float(idx.ef.mean()), 2)})
    log.info("=== Stage 13 complete: %d echos; EF-category %s ===", len(idx), dist)
    print(f"echo_indexed={len(idx)} dist={dist}")


if __name__ == "__main__":
    main()
