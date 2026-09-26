#!/usr/bin/env python3
"""Stage 06 — match ONE external PTB-XL ECG per case, download it, convert it.

Matching uses only broad, non-identifying features (age band, sex, broad cardiac
category). Assignment is DISTINCT (no ECG reused across cases) and deterministic.
Every assignment records that the ECG and the EHR are DIFFERENT deidentified
individuals combined only for multimodal software testing.

Converted artifacts are cached under cache/ecg/<ecg_id>/ and copied into each case
directory by stage 09. Download/convert failures are non-fatal: the case is simply
packaged without an ECG.
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import classify as X  # noqa: E402

PTBXL_ROOT = "https://physionet.org/files/ptb-xl/1.0.1/"
ECG_CACHE = C.CACHE / "ecg"
STAGE = C.STAGING / "eicu"
DONOR_WARNING = ("The ECG and EHR originate from different deidentified individuals "
                 "and are combined only for multimodal software testing.")


def desired_bucket(cv_categories):
    for cat in cv_categories:
        if cat in X.CV_BROAD_FOR_ECG:
            return X.CV_BROAD_FOR_ECG[cat]
    return "ischemia_sttc" if cv_categories else "normal"


def rank_key(row, want_bucket, want_sex, want_band):
    score = 0
    if row["broad_bucket"] == want_bucket:
        score += 4
    if row["sex"] == want_sex:
        score += 2
    if row["age_band"] == want_band:
        score += 1
    return (-score, row["ecg_id"])


def _normalize_wfdb(outdir: Path, base: str) -> None:
    """Rename the downloaded <base>.hea/.dat pair to ecg.hea/ecg.dat so the
    record loads standalone. The .dat bytes are copied verbatim (waveform
    untouched); only the header's internal filename references are rewritten."""
    hea_txt = (outdir / f"{base}.hea").read_text()
    (outdir / "ecg.hea").write_text(hea_txt.replace(base, "ecg"))
    shutil.copyfile(outdir / f"{base}.dat", outdir / "ecg.dat")
    for f in (outdir / f"{base}.hea", outdir / f"{base}.dat"):
        if f.exists() and f.name not in ("ecg.hea", "ecg.dat"):
            f.unlink()


def convert_ecg(outdir: Path, ecg_id, log):
    """Read the normalized ecg.hea/ecg.dat, write ecg.csv/ecg.json/ecg.png. Returns meta."""
    import json
    import numpy as np
    import wfdb
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rec = wfdb.rdrecord(str(outdir / "ecg"))
    sig = rec.p_signal  # (n, 12) in mV
    fs = rec.fs
    names = [n.upper() for n in rec.sig_name]
    col_for = {"I": "lead_I", "II": "lead_II", "III": "lead_III", "AVR": "aVR",
               "AVL": "aVL", "AVF": "aVF", "V1": "V1", "V2": "V2", "V3": "V3",
               "V4": "V4", "V5": "V5", "V6": "V6"}
    ordered = ["lead_I", "lead_II", "lead_III", "aVR", "aVL", "aVF",
               "V1", "V2", "V3", "V4", "V5", "V6"]
    idx = {col_for.get(names[i], names[i]): i for i in range(len(names))}
    n = sig.shape[0]
    t = np.arange(n) / fs

    # ecg.csv
    with open(outdir / "ecg.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time_seconds"] + ordered)
        for k in range(n):
            row = [round(float(t[k]), 4)]
            for c in ordered:
                j = idx.get(c)
                row.append("" if j is None else round(float(sig[k, j]), 5))
            w.writerow(row)

    # ecg.json
    signals = {c: [round(float(sig[k, idx[c]]), 5) for k in range(n)] if c in idx else []
               for c in ordered}
    meta = {"ecg_source": "PTB-XL", "ecg_record_id": str(ecg_id), "sampling_rate_hz": float(fs),
            "n_samples": int(n), "duration_seconds": round(n / fs, 3), "units": "mV",
            "leads": ordered, "signals": signals}
    with open(outdir / "ecg.json", "w") as fh:
        json.dump(meta, fh)

    # ecg.png (12-lead stacked)
    fig, axes = plt.subplots(12, 1, figsize=(10, 12), sharex=True)
    for ax, c in zip(axes, ordered):
        j = idx.get(c)
        if j is not None:
            ax.plot(t, sig[:, j], linewidth=0.6, color="#111")
        ax.set_ylabel(c, rotation=0, labelpad=18, fontsize=8, va="center")
        ax.set_yticks([]); ax.grid(True, color="#f0c0c0", linewidth=0.3)
    axes[-1].set_xlabel("time (s)")
    fig.suptitle(f"PTB-XL ECG {ecg_id} — external modality (not the eICU patient)", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(outdir / "ecg.png", dpi=90)
    plt.close(fig)

    return {"sampling_rate_hz": float(fs), "n_samples": int(n),
            "duration_seconds": round(n / fs, 3)}


def main() -> None:
    import pandas as pd
    C.ensure_dirs()
    ECG_CACHE.mkdir(parents=True, exist_ok=True)
    log = C.get_logger("06_download_selected_ecgs")
    log.info("=== Stage 06: ECG match + download + convert ===")

    sel_path = STAGE / "cohort_selection.csv"
    if not sel_path.exists():
        sys.exit("FATAL: cohort_selection.csv missing — run 04 first")
    sel = pd.read_csv(sel_path)
    for a in sys.argv:
        if a.startswith("--limit="):
            sel = sel.head(int(a.split("=", 1)[1]))
    idx = pd.read_parquet(C.STAGING / "ptb-xl" / "ptbxl_index.parquet")
    pool = idx.to_dict("records")
    log.info("cases=%d ecg_pool=%d", len(sel), len(pool))

    used = set()
    assignments = []
    ok = fail = 0
    for _, crow in sel.iterrows():
        stay = int(crow["patientunitstayid"])
        case = crow["case_id"]
        asm = C.read_json(STAGE / "assembled" / f"{stay}.json")
        cvcats = asm.get("cv_categories", [])
        want_bucket = desired_bucket(cvcats)
        want_sex = (asm["demographics"].get("gender") or "unknown")
        want_band = asm["demographics"].get("age_band", "unknown")

        cands = sorted((r for r in pool if r["ecg_id"] not in used),
                       key=lambda r: rank_key(r, want_bucket, want_sex, want_band))
        if not cands:
            log.warning("%s: no ECG candidates left", case)
            assignments.append({"case_id": case, "patientunitstayid": stay, "ecg_record_id": "",
                                "assigned": False})
            fail += 1
            continue
        chosen = cands[0]
        eid = int(chosen["ecg_id"])
        used.add(eid)

        # download hea/dat into cache if not already converted
        outdir = ECG_CACHE / str(eid)
        outdir.mkdir(parents=True, exist_ok=True)
        need_convert = not (outdir / "ecg.csv").exists()
        if need_convert:
            fn = chosen["filename_lr"]  # e.g. records100/00000/00001_lr
            base = Path(fn).name          # e.g. 00001_lr
            base_url = PTBXL_ROOT + fn
            try:
                C.download(base_url + ".hea", outdir / f"{base}.hea", logger=log, retries=3, timeout=40)
                C.download(base_url + ".dat", outdir / f"{base}.dat", logger=log, retries=3,
                           timeout=60, expect_min_bytes=1000)
                _normalize_wfdb(outdir, base)
                meta = convert_ecg(outdir, eid, log)
            except Exception as e:
                log.warning("%s: ECG %s download/convert failed: %s", case, eid, e)
                assignments.append({"case_id": case, "patientunitstayid": stay,
                                    "ecg_record_id": str(eid), "assigned": False, "error": str(e)})
                fail += 1
                continue
        else:
            meta = C.read_json(outdir / "ecg.json")
            meta = {"sampling_rate_hz": meta.get("sampling_rate_hz"),
                    "n_samples": meta.get("n_samples"),
                    "duration_seconds": meta.get("duration_seconds")}

        match_features = []
        if chosen["broad_bucket"] == want_bucket:
            match_features.append("broad_cardiac_category")
        if chosen["sex"] == want_sex:
            match_features.append("sex")
        if chosen["age_band"] == want_band:
            match_features.append("age_band")
        assignments.append({
            "case_id": case, "patientunitstayid": stay, "ecg_record_id": str(eid),
            "assigned": True, "ecg_source": "PTB-XL", "linkage_type": "matched_external_modality",
            "same_patient_as_ehr": False,
            "desired_bucket": want_bucket, "ecg_bucket": chosen["broad_bucket"],
            "ecg_primary_superclass": chosen["primary_superclass"], "ecg_rhythm": chosen["rhythm"],
            "ecg_sex": chosen["sex"], "ecg_age_band": chosen["age_band"],
            "match_features": "|".join(match_features),
            "sampling_rate_hz": meta.get("sampling_rate_hz"),
            "n_samples": meta.get("n_samples"), "duration_seconds": meta.get("duration_seconds"),
            "warning": DONOR_WARNING,
        })
        ok += 1
        if ok % 50 == 0:
            log.info("assigned+converted %d ECGs so far", ok)

    # persist assignments
    cols = ["case_id", "patientunitstayid", "ecg_record_id", "assigned", "ecg_source",
            "linkage_type", "same_patient_as_ehr", "desired_bucket", "ecg_bucket",
            "ecg_primary_superclass", "ecg_rhythm", "ecg_sex", "ecg_age_band",
            "match_features", "sampling_rate_hz", "n_samples", "duration_seconds", "warning"]
    C.COHORT.mkdir(parents=True, exist_ok=True)
    with open(C.COHORT / "ecg_assignments.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for a in assignments:
            w.writerow(a)
    C.write_json(C.STAGING / "ptb-xl" / "ecg_assignments.json", assignments)
    log.info("=== Stage 06 complete: assigned=%d failed=%d ===", ok, fail)
    print(f"ecg_assigned={ok} ecg_failed={fail}")


if __name__ == "__main__":
    main()
