"""Shared helpers + source registry for the CT imaging + VISTA extension.

Reuses the base data pipeline's `_common` (paths, download, sha256, json) and adds
imaging-specific paths, the approved-source registry with real access status, and
manifest writers. Import-cheap.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# reuse the base pipeline common lib (data/scripts/_common.py)
_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
import _common as C  # noqa: E402

# also make the repo python/ importable for the imaging package
REPO_ROOT = C.REPO_ROOT
sys.path.insert(0, str(REPO_ROOT))

# ---- imaging paths -------------------------------------------------------- #
RAW = C.RAW
RAW_MULTID4CAD = RAW / "multid4cad"
RAW_IMAGECAS = RAW / "imagecas"
RAW_TOTALSEG = RAW / "totalsegmentator"
RAW_TCIA = RAW / "tcia"
RAW_RADCHEST = RAW / "rad-chestct"

STAGING_IMAGING = C.STAGING / "imaging"
STG_DICOM = STAGING_IMAGING / "dicom"
STG_NIFTI = STAGING_IMAGING / "nifti"
STG_NORMALIZED = STAGING_IMAGING / "normalized"
STG_VISTA_JOBS = STAGING_IMAGING / "vista-jobs"
STG_VISTA_RESULTS = STAGING_IMAGING / "vista-results"

IMAGING_CASES = C.DATA_DIR / "imaging-cases"
VISTA_BENCHMARK = C.DATA_DIR / "vista-benchmark"
VB_MANIFESTS = VISTA_BENCHMARK / "manifests"
VB_INPUTS = VISTA_BENCHMARK / "inputs"
VB_REFERENCES = VISTA_BENCHMARK / "references"
VB_PREDICTIONS = VISTA_BENCHMARK / "predictions"
VB_METRICS = VISTA_BENCHMARK / "metrics"

ANALYSIS_IMAGING = C.ANALYSIS / "imaging"
AI_LINKAGE = ANALYSIS_IMAGING / "linkage"
AI_VISTA = ANALYSIS_IMAGING / "vista"
AI_FUSION = ANALYSIS_IMAGING / "fusion"
AI_CHARTS = ANALYSIS_IMAGING / "charts"

QUAR_LINKAGE = C.QUARANTINE / "imaging-linkage"
QUAR_CORRUPT = C.QUARANTINE / "corrupt-volumes"
QUAR_UNSUPPORTED = C.QUARANTINE / "unsupported-modalities"
QUAR_INVALID_VISTA = C.QUARANTINE / "invalid-vista-results"

CASES = C.CASES
COHORT = C.COHORT

IMAGING_SOURCE_MANIFEST_JSON = C.DATA_DIR / "imaging_source_manifest.json"
IMAGING_SOURCE_MANIFEST_CSV = C.DATA_DIR / "imaging_source_manifest.csv"

ALL_IMAGING_DIRS = [
    RAW_MULTID4CAD, RAW_IMAGECAS, RAW_TOTALSEG, RAW_TCIA, RAW_RADCHEST,
    STG_DICOM, STG_NIFTI, STG_NORMALIZED, STG_VISTA_JOBS, STG_VISTA_RESULTS,
    IMAGING_CASES, VB_MANIFESTS, VB_INPUTS, VB_REFERENCES, VB_PREDICTIONS, VB_METRICS,
    ANALYSIS_IMAGING, AI_LINKAGE, AI_VISTA, AI_FUSION, AI_CHARTS,
    QUAR_LINKAGE, QUAR_CORRUPT, QUAR_UNSUPPORTED, QUAR_INVALID_VISTA,
]


def ensure_dirs() -> None:
    C.ensure_dirs()
    for d in ALL_IMAGING_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


# ---- approved-source registry (spec §6/§9) -------------------------------- #
# Access status reflects the real, documented state. Controlled sources stay
# access_pending unless local files exist AND the DUA/license flag is set.
SOURCES = {
    "multid4cad": {
        "source_id": "multid4cad",
        "source_name": "MultiD4CAD — multimodal cardiac CT (CAD)",
        "version_env": "MULTID4CAD_VERSION",
        "doi": "10.5281/zenodo.15148653",
        "license": "Controlled access — Zenodo restricted; signed DUA required",
        "access_type": "controlled",
        "enabled_env": "MULTID4CAD_ENABLED",
        "root_env": "MULTID4CAD_ROOT",
        "access_flag_env": "MULTID4CAD_ACCESS_APPROVED",
        "dua_flag_env": "MULTID4CAD_DUA_RECORDED",
        "dua_required": True,
        "image_modality": ["CT"],
        "image_formats": ["nifti"],
        "has_same_subject_clinical_data": True,
        "has_reference_masks": True,   # EAT/PAT masks (VISTA cannot resolve these classes)
        "clinical_metadata_fields": ["cad_label", "clinical_features"],
        "subject_id_field": "sample_id", "study_id_field": "sample_id", "series_id_field": "sample_id",
        "tier": 1, "expected_max_cases": 118,
        "approved_uses": ["imaging_native_same_subject cases", "EAT/PAT reference (endpoint-permitting)"],
        "prohibited_uses": ["fusing into an eICU subject", "bypassing access controls"],
    },
    "imagecas": {
        "source_id": "imagecas",
        "source_name": "ImageCAS — coronary CTA segmentation benchmark (~1000 scans)",
        "version_env": "IMAGECAS_VERSION",
        "doi": None,
        "license": "Controlled request; license must be recorded",
        "access_type": "controlled",
        "enabled_env": "IMAGECAS_ENABLED",
        "root_env": "IMAGECAS_ROOT",
        "access_flag_env": "IMAGECAS_LICENSE_RECORDED",
        "dua_flag_env": "IMAGECAS_LICENSE_RECORDED",
        "dua_required": True,
        "image_modality": ["CT"],
        "image_formats": ["nifti"],
        "has_same_subject_clinical_data": False,
        "has_reference_masks": True,   # coronary-artery masks (VISTA cannot resolve coronary)
        "clinical_metadata_fields": [],
        "subject_id_field": "case_id", "study_id_field": "case_id", "series_id_field": "case_id",
        "tier": 3, "expected_max_cases": 1000,
        "approved_uses": ["imaging_only benchmark", "throughput/quality analysis"],
        "prohibited_uses": ["inventing meds/labs", "attaching to an eICU patient",
                            "coronary Dice unless endpoint supports coronary target"],
    },
    "totalsegmentator": {
        "source_id": "totalsegmentator",
        "source_name": "TotalSegmentator dataset — multi-organ CT reference masks",
        "version_env": "TOTALSEGMENTATOR_DATASET_VERSION",
        "doi": "10.5281/zenodo.10047292",
        "license": "CC BY 4.0 (open); example files under the Apache-2.0 repo",
        "access_type": "open",
        "enabled_env": "TOTALSEGMENTATOR_DATASET_ENABLED",
        "root_env": "TOTALSEGMENTATOR_DATASET_ROOT",
        "access_flag_env": "TOTALSEGMENTATOR_LICENSE_RECORDED",
        "dua_flag_env": "TOTALSEGMENTATOR_LICENSE_RECORDED",
        "dua_required": False,
        "image_modality": ["CT"],
        "image_formats": ["nifti", "dicom"],
        "has_same_subject_clinical_data": False,
        "has_reference_masks": True,
        "clinical_metadata_fields": [],
        "subject_id_field": "subject_id", "study_id_field": "subject_id", "series_id_field": "subject_id",
        "tier": 4, "expected_max_cases": 1228,
        "approved_uses": ["imaging_only benchmark", "organ Dice/HD95 vs overlapping VISTA labels",
                          "DICOM/NIfTI validation"],
        "prohibited_uses": ["attaching to an eICU patient", "diagnosis"],
    },
    "tcia": {
        "source_id": "tcia", "source_name": "TCIA collections (varied)",
        "version_env": None, "doi": None,
        "license": "Per-collection; must be recorded", "access_type": "restricted",
        "enabled_env": "TCIA_ENABLED", "root_env": None,
        "access_flag_env": "TCIA_ENABLED", "dua_flag_env": "TCIA_ENABLED", "dua_required": True,
        "image_modality": ["CT"], "image_formats": ["dicom"],
        "has_same_subject_clinical_data": False, "has_reference_masks": False,
        "clinical_metadata_fields": [], "subject_id_field": "PatientID",
        "study_id_field": "StudyInstanceUID", "series_id_field": "SeriesInstanceUID",
        "tier": 2, "expected_max_cases": 0,
        "approved_uses": ["only with verified same-subject linkage document"],
        "prohibited_uses": ["assuming clinical metadata exists"],
    },
    "rad-chestct": {
        "source_id": "rad-chestct", "source_name": "RAD-ChestCT — chest CT + report labels",
        "version_env": None, "doi": None,
        "license": "Controlled; must be recorded", "access_type": "controlled",
        "enabled_env": "RAD_CHESTCT_ENABLED", "root_env": None,
        "access_flag_env": "RAD_CHESTCT_ENABLED", "dua_flag_env": "RAD_CHESTCT_ENABLED",
        "dua_required": True, "image_modality": ["CT"], "image_formats": ["nifti", "npz"],
        "has_same_subject_clinical_data": False, "has_reference_masks": False,
        "clinical_metadata_fields": ["report_labels"], "subject_id_field": "scan_id",
        "study_id_field": "scan_id", "series_id_field": "scan_id",
        "tier": 5, "expected_max_cases": 0,
        "approved_uses": ["imaging analysis with verified scan id"],
        "prohibited_uses": ["inventing missing clinical context"],
    },
}


def source_access_state(sid: str) -> dict:
    """Return the real access state for a source from env + local files."""
    s = SOURCES[sid]
    enabled = env_bool(s["enabled_env"], False)
    root = env(s["root_env"]) if s.get("root_env") else ""
    access_ok = env_bool(s["access_flag_env"], False)
    dua_ok = env_bool(s["dua_flag_env"], False)
    local_present = bool(root) and Path(root).exists()
    # totalsegmentator example subset lives under RAW_TOTALSEG regardless of root
    if sid == "totalsegmentator" and any(RAW_TOTALSEG.glob("**/*.nii.gz")):
        local_present = True
    if s["access_type"] == "open":
        access_verified = enabled
    else:
        access_verified = enabled and access_ok and (dua_ok or not s["dua_required"])
    return {"enabled": enabled, "root": root or None, "local_present": local_present,
            "access_approved": access_ok, "dua_recorded": dua_ok,
            "access_verified": access_verified, "version": env(s["version_env"]) if s.get("version_env") else None}
