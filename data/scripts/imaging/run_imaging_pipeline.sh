#!/usr/bin/env bash
# HeartTwin CareGuard — CT imaging + VISTA extension pipeline.
# Additive + idempotent + resumable. Gated: with no live VISTA endpoint and no
# approved controlled-dataset access, it audits, ingests open CT, validates, and
# prepares (but does not fake) segmentation.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$(cd "$HERE/../.." && pwd)"
cd "$DATA_DIR"
PY="$DATA_DIR/.venv-data/bin/python"

# Source-access flags (mirror .env.example defaults). Controlled sources stay
# access_pending unless their approval/DUA flags are set here after signing.
export MULTID4CAD_ENABLED="${MULTID4CAD_ENABLED:-true}"
export IMAGECAS_ENABLED="${IMAGECAS_ENABLED:-true}"
export TOTALSEGMENTATOR_DATASET_ENABLED="${TOTALSEGMENTATOR_DATASET_ENABLED:-true}"
export TOTALSEGMENTATOR_LICENSE_RECORDED="${TOTALSEGMENTATOR_LICENSE_RECORDED:-true}"
export TOTALSEGMENTATOR_SUBSET_SIZE="${TOTALSEGMENTATOR_SUBSET_SIZE:-6}"

LOG="$DATA_DIR/logs/run_imaging.log"
run() { echo "--- $* ---" | tee -a "$LOG"; "$PY" "$@" 2>&1 | tee -a "$LOG"; }

echo "=== imaging pipeline start $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee -a "$LOG"
run scripts/imaging/00_audit_existing_ct_linkage.py
run scripts/imaging/01_discover_imaging_sources.py
run scripts/imaging/02_verify_imaging_licenses.py
run scripts/imaging/04_import_multid4cad.py
run scripts/imaging/05_import_imagecas.py
run scripts/imaging/06_import_totalsegmentator.py
run scripts/imaging/07_import_tcia.py
run scripts/imaging/08_validate_dicom.py
run scripts/imaging/09_convert_dicom_to_nifti.py
run scripts/imaging/14_build_imaging_native_cases.py
run scripts/imaging/03_build_imaging_manifest.py
run scripts/imaging/10_prepare_vista_jobs.py
run scripts/imaging/11_run_vista_jobs.py
run scripts/imaging/12_validate_vista_outputs.py
run scripts/imaging/13_compute_segmentation_metrics.py
run scripts/imaging/15_fuse_verified_imaging.py
run scripts/imaging/16_update_fhir_imaging.py
run scripts/imaging/17_run_imaging_analysis.py
run scripts/imaging/18_validate_imaging_pipeline.py
echo "=== imaging pipeline done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee -a "$LOG"
