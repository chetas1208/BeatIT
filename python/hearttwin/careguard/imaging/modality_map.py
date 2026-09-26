"""Per-case CT + echocardiography modality mapping (matched external modality).

SAFETY: these are composite research cases (clinical from eICU, ECG from PTB-XL —
different individuals). Same-subject CT/echo does not exist, so — exactly like the
existing ECG handling and the teammate's `linkage.py` — CT/echo are mapped as
**matched external research modalities**, never as same-subject clinical fusion.
Echo brings real EF/ESV/EDV (EchoNet-Dynamic); CT brings a VISTA-segmentable
volume when a local one exists. Every mapping is labeled and clinician-review-gated.
"""

from __future__ import annotations

import csv
import hashlib
import pathlib
from functools import lru_cache
from typing import Any

_ECHONET = pathlib.Path("data/raw/echonet/FileList.csv")
_ECHONET_VIDEOS = pathlib.Path("data/raw/echonet/Videos")
# The one locally-present CT volume (TotalSegmentator open example, CC BY 4.0).
_TS_CT = pathlib.Path("data/raw/totalsegmentator/nifti/ts_example_full/ct.nii.gz")

EXTERNAL_LABEL = (
    "Matched external research modality — NOT the same individual as this case's "
    "clinical record. For research/simulation and clinician review only."
)


@lru_cache(maxsize=1)
def _echonet_rows() -> list[dict[str, Any]]:
    if not _ECHONET.exists():
        return []
    rows: list[dict[str, Any]] = []
    with _ECHONET.open() as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "file": r["FileName"],
                    "ef": float(r["EF"]), "esv": float(r["ESV"]), "edv": float(r["EDV"]),
                    "fps": float(r.get("FPS", 0) or 0), "frames": int(float(r.get("NumberOfFrames", 0) or 0)),
                    "split": r.get("Split", ""),
                })
            except (KeyError, ValueError):
                continue
    return rows


def _stable_index(case_id: str, n: int) -> int:
    if n <= 0:
        return 0
    h = int(hashlib.sha256(case_id.encode()).hexdigest(), 16)
    return h % n


def _expected_ef_band(cardiac_conditions: list[str]) -> tuple[float, float, str]:
    """Pick a clinically-coherent EF band from the case's cardiac phenotype.
    A 'related' match (realistic EF for the phenotype) — still external/not-same-subject."""
    text = " ".join(c.lower() for c in cardiac_conditions)
    if any(k in text for k in ("hfref", "reduced ejection", "systolic heart failure", "cardiomyopathy")):
        return (20.0, 40.0, "reduced (HFrEF-like)")
    if "heart failure" in text:
        return (30.0, 50.0, "reduced-to-mid")
    return (52.0, 75.0, "preserved/normal")


def map_echo(case_id: str, cardiac_conditions: list[str] | None = None) -> dict[str, Any]:
    rows = _echonet_rows()
    if not rows:
        return {"available": False, "modality": "echocardiography",
                "reason": "EchoNet FileList.csv not present locally.", "label": EXTERNAL_LABEL}
    lo, hi, band = _expected_ef_band(cardiac_conditions or [])
    pool = [r for r in rows if lo <= r["ef"] <= hi] or rows
    rec = pool[_stable_index(case_id, len(pool))]
    video_present = (_ECHONET_VIDEOS / f"{rec['file']}.avi").exists()
    return {
        "available": True,
        "modality": "echocardiography",
        "source_dataset": "EchoNet-Dynamic",
        "source_record_id": rec["file"],
        "same_subject_as_clinical_record": False,
        "linkage_type": "matched_external_research_modality",
        "match_features": {"expected_ef_band": band, "matched_ef_range": [lo, hi]},
        "derived_measurements": {
            "ejection_fraction_pct": round(rec["ef"], 2),
            "end_systolic_volume_ml": round(rec["esv"], 2),
            "end_diastolic_volume_ml": round(rec["edv"], 2),
            "stroke_volume_ml": round(rec["edv"] - rec["esv"], 2),
        },
        "video_present": video_present,
        "video_path": f"data/raw/echonet/Videos/{rec['file']}.avi" if video_present else None,
        "echo_analysis_model": "EchoNet-Dynamic (EF/ESV/EDV); VISTA-3D does NOT process echo/ultrasound.",
        "label": EXTERNAL_LABEL,
        "clinician_review_required": True,
    }


def map_ct(case_id: str) -> dict[str, Any]:
    ct_present = _TS_CT.exists()
    return {
        "available": ct_present,
        "modality": "ct",
        "source_dataset": "TotalSegmentator (open, CC BY 4.0)" if ct_present else None,
        "same_subject_as_clinical_record": False,
        "linkage_type": "matched_external_research_modality" if ct_present else "no_linked_ct",
        "ct_volume_path": str(_TS_CT) if ct_present else None,
        "vista_eligible": ct_present,   # research segmentation only, not clinical fusion
        "reason": None if ct_present else "No local same-subject CT pixel data for this composite case.",
        "label": EXTERNAL_LABEL,
        "clinician_review_required": True,
    }


def build_imaging_map(case_id: str, cardiac_conditions: list[str] | None = None) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "echocardiography": map_echo(case_id, cardiac_conditions),
        "ct": map_ct(case_id),
        "safety_note": "External research modalities are never fused into clinical reasoning as "
                       "same-subject data; they support simulation and clinician review only.",
    }
