#!/usr/bin/env python3
"""Stage 14 — match ONE external EchoNet echo per case, download + convert it.

Matching uses only the non-identifying EF category (EchoNet exposes no age/sex).
Assignment is DISTINCT and deterministic. Every echo is a MATCHED EXTERNAL MODALITY:
same_patient_as_ehr=false, with a donor warning. The echo's EF/EDV/ESV are the
DONOR'S measurements and are never presented as the eICU patient's values.

Converted artifacts (echo.avi + echo-frame.png + echo.gif + echo.json + provenance)
are cached under cache/echo/<echo_id>/ and copied into each case by stage 09.
Download/convert failures are non-fatal (case packaged without echo).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

HF_BASE = "https://huggingface.co/datasets/miyuki17/EchoNet-Dynamic-unzipped/resolve/main/"
ECHO_CACHE = C.CACHE / "echo"
STAGE = C.STAGING / "eicu"
DONOR_WARNING = ("The echocardiogram is a matched external modality from EchoNet-Dynamic "
                 "and does not originate from the same individual as the eICU record. Its "
                 "EF/EDV/ESV are the echo donor's measurements, not the eICU patient's.")

# case cardiovascular context -> desired echo EF category
CV_TO_EF = {
    "heart_failure": "reduced", "cardiomyopathy": "reduced",
    "myocardial_infarction_acs": "mid", "coronary_artery_disease": "mid",
    "valvular_disease": "preserved", "hypertension": "preserved",
}


def desired_ef_category(cv_categories):
    for c in cv_categories:
        if c in CV_TO_EF:
            return CV_TO_EF[c]
    return "preserved"


def convert_echo(avi_path: Path, echo_id, meta, log):
    import numpy as np
    import imageio.v3 as iio
    outdir = ECHO_CACHE / str(echo_id)
    frames = iio.imread(avi_path, plugin="FFMPEG")  # (T,H,W,C) via imageio-ffmpeg
    frames = np.asarray(frames)
    if frames.ndim == 3:  # (T,H,W) grayscale -> add channel
        frames = np.stack([frames] * 3, axis=-1)
    t = frames.shape[0]
    iio.imwrite(outdir / "echo-frame.png", frames[t // 2])
    # downsampled animated GIF for the demo (~24 frames)
    step = max(1, t // 24)
    sub = [frames[i] for i in range(0, t, step)][:24]
    iio.imwrite(outdir / "echo.gif", sub, extension=".gif", loop=0, duration=120)
    return t


def main() -> None:
    import pandas as pd
    C.ensure_dirs()
    ECHO_CACHE.mkdir(parents=True, exist_ok=True)
    log = C.get_logger("14_match_download_echos")
    log.info("=== Stage 14: echo match + download + convert ===")

    sel = pd.read_csv(STAGE / "cohort_selection.csv")
    for a in sys.argv:
        if a.startswith("--limit="):
            sel = sel.head(int(a.split("=", 1)[1]))
    idx = pd.read_parquet(C.STAGING / "echonet" / "echo_index.parquet")
    pool = idx.to_dict("records")
    log.info("cases=%d echo_pool=%d", len(sel), len(pool))

    used, assignments, ok, fail = set(), [], 0, 0
    for _, crow in sel.iterrows():
        stay = int(crow["patientunitstayid"])
        case = crow["case_id"]
        asm = C.read_json(C.STAGING / "assembled" / f"{case}.json")
        cvcats = asm.get("cv_categories", [])
        want = desired_ef_category(cvcats)

        cands = sorted((r for r in pool if r["echo_id"] not in used),
                       key=lambda r: (r["ef_category"] != want, r["echo_id"]))
        if not cands:
            assignments.append({"case_id": case, "patientunitstayid": stay, "echo_id": "",
                                "assigned": False})
            fail += 1
            continue
        chosen = cands[0]
        eid = chosen["echo_id"]
        used.add(eid)
        outdir = ECHO_CACHE / str(eid)
        outdir.mkdir(parents=True, exist_ok=True)
        need = not (outdir / "echo.gif").exists()
        if need:
            try:
                C.download(HF_BASE + chosen["video_path"], outdir / "echo.avi",
                           logger=log, retries=3, timeout=90, expect_min_bytes=5000)
                convert_echo(outdir / "echo.avi", eid, chosen, log)
            except Exception as e:
                log.warning("%s: echo %s failed: %s", case, eid, e)
                assignments.append({"case_id": case, "patientunitstayid": stay,
                                    "echo_id": eid, "assigned": False, "error": str(e)})
                fail += 1
                continue
        # echo.json (metadata + donor labeling) + provenance
        echo_meta = {
            "echo_source": "EchoNet-Dynamic", "echo_record_id": eid,
            "linkage_type": "matched_external_modality", "same_patient_as_ehr": False,
            "modality": "US", "view": "apical_4_chamber",
            "match_features": ["broad_cardiac_category_via_ef"], "matched_ef_category": chosen["ef_category"],
            "desired_ef_category": want,
            "donor_measurements": {"ejection_fraction_pct": chosen["ef"], "edv_ml": chosen["edv"],
                                   "esv_ml": chosen["esv"], "note": "donor values — NOT the eICU patient's"},
            "fps": chosen["fps"], "frames": chosen["frames"],
            "height": chosen["height"], "width": chosen["width"],
            "warning": DONOR_WARNING}
        C.write_json(outdir / "echo.json", echo_meta)
        C.write_json(outdir / "echo-provenance.json", {
            "echo_source": "EchoNet-Dynamic", "echo_record_id": eid,
            "linkage_type": "matched_external_modality", "same_patient_as_ehr": False,
            "warning": DONOR_WARNING, "license": "Stanford EchoNet Research Use Agreement (via mirror)",
            "video_path": chosen["video_path"]})
        assignments.append({
            "case_id": case, "patientunitstayid": stay, "echo_id": eid, "assigned": True,
            "echo_source": "EchoNet-Dynamic", "linkage_type": "matched_external_modality",
            "same_patient_as_ehr": False, "modality": "US", "view": "apical_4_chamber",
            "desired_ef_category": want, "echo_ef_category": chosen["ef_category"],
            "donor_ef": chosen["ef"], "donor_edv": chosen["edv"], "donor_esv": chosen["esv"],
            "fps": chosen["fps"], "frames": chosen["frames"], "warning": DONOR_WARNING})
        ok += 1
        if ok % 50 == 0:
            log.info("assigned+converted %d echos", ok)

    cols = ["case_id", "patientunitstayid", "echo_id", "assigned", "echo_source", "linkage_type",
            "same_patient_as_ehr", "modality", "view", "desired_ef_category", "echo_ef_category",
            "donor_ef", "donor_edv", "donor_esv", "fps", "frames", "warning"]
    C.COHORT.mkdir(parents=True, exist_ok=True)
    with open(C.COHORT / "echo_assignments.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for a in assignments:
            w.writerow(a)
    C.write_json(C.STAGING / "echonet" / "echo_assignments.json", assignments)
    log.info("=== Stage 14 complete: assigned=%d failed=%d ===", ok, fail)
    print(f"echo_assigned={ok} echo_failed={fail}")


if __name__ == "__main__":
    main()
