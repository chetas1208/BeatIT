"""Absolute CT-imaging linkage rule (the safety core of the imaging extension).

A CT scan may be fused into a clinical case ONLY when same-subject identity is
independently verified via one of:

  Rule A — native same-subject dataset (image + clinical metadata distributed
           together, sharing the dataset's own subject/sample ID);
  Rule B — official cross-dataset linkage document from the source publisher;
  Rule C — existing local dataset linkage whose subject+study IDs verify against
           the original source manifest.

Demographic / phenotype / diagnosis / ECG-class / nearest-neighbour / random /
filename similarity NEVER prove identity and MUST NOT drive fusion.

This module is import-cheap and dependency-free so every script and test can use
it as the single source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# ---- Linkage status vocabulary (spec §3) --------------------------------- #
SAME_SUBJECT_VERIFIED = "same_subject_verified"
IMAGING_NATIVE_SAME_SUBJECT = "imaging_native_same_subject"
IMAGING_ONLY = "imaging_only"
NO_LINKED_CT = "no_linked_ct"
ACCESS_PENDING = "access_pending"
INVALID = "invalid"
PROHIBITED = "prohibited_cross_dataset_match"

ALL_STATUSES = (SAME_SUBJECT_VERIFIED, IMAGING_NATIVE_SAME_SUBJECT, IMAGING_ONLY,
                NO_LINKED_CT, ACCESS_PENDING, INVALID, PROHIBITED)

# Only these two statuses permit fusion into a clinical case.
FUSION_ALLOWED_STATUSES = frozenset({SAME_SUBJECT_VERIFIED, IMAGING_NATIVE_SAME_SUBJECT})

# Linkage evidence kinds that are ACCEPTED (map to Rule A/B/C).
VALID_LINKAGE_METHODS = frozenset({
    "native_same_subject_dataset",      # Rule A
    "official_cross_dataset_mapping",   # Rule B
    "local_source_manifest_verified",   # Rule C
})

# Linkage "evidence" kinds that are NEVER sufficient (spec §2 never-permitted).
PROHIBITED_LINKAGE_METHODS = frozenset({
    "same_age", "same_sex", "same_diagnosis", "same_cardiac_category",
    "similar_labs", "similar_medications", "nearest_neighbor", "embedding",
    "matching_phenotype", "matching_ecg_class", "same_hospital_type",
    "random_assignment", "model_generated_matching", "filename_similarity",
})


@dataclass
class CtImagingLinkage:
    """The `ct_imaging` block stamped into every case manifest (spec §3)."""
    status: str = NO_LINKED_CT
    source_dataset: str | None = None
    source_subject_id: str | None = None
    source_study_id: str | None = None
    source_series_id: str | None = None
    same_subject_as_clinical_record: bool = False
    linkage_evidence: list = field(default_factory=list)
    linkage_manifest_path: str | None = None
    linkage_confidence: str = "unavailable"   # verified | unavailable | prohibited
    vista_eligible: bool = False
    reason: str = ""

    def to_dict(self) -> dict:
        return {"ct_imaging": asdict(self)}


def is_fusion_allowed(status: str) -> bool:
    """The single gate every fusion path MUST call. True only for verified
    same-subject / imaging-native-same-subject linkage."""
    return status in FUSION_ALLOWED_STATUSES


def classify_linkage_method(method: str | None) -> str:
    """Return 'valid' | 'prohibited' | 'unknown' for a proposed linkage method."""
    if not method:
        return "unknown"
    m = method.strip().lower()
    if m in VALID_LINKAGE_METHODS:
        return "valid"
    if m in PROHIBITED_LINKAGE_METHODS:
        return "prohibited"
    return "unknown"


def evaluate_linkage(
    *,
    method: str | None,
    source_dataset: str | None,
    source_subject_id: str | None,
    linked_clinical_subject_id: str | None,
    access_approved: bool = True,
    has_actual_volume: bool = True,
    native_same_subject: bool = False,
) -> CtImagingLinkage:
    """Derive a linkage status from concrete evidence, rejecting any prohibited
    method. This is the ONLY sanctioned way to produce a fusion-eligible status.
    """
    kind = classify_linkage_method(method)
    if kind == "prohibited":
        return CtImagingLinkage(
            status=PROHIBITED, source_dataset=source_dataset,
            source_subject_id=source_subject_id, same_subject_as_clinical_record=False,
            linkage_confidence="prohibited", vista_eligible=False,
            reason=f"Prohibited linkage method '{method}': demographic/phenotype/"
                   "similarity/random/filename matching never proves identity.")
    if not has_actual_volume:
        return CtImagingLinkage(
            status=NO_LINKED_CT, source_dataset=source_dataset,
            reason="No retrievable CT pixel volume (report/reference only).")
    if not access_approved:
        return CtImagingLinkage(
            status=ACCESS_PENDING, source_dataset=source_dataset,
            source_subject_id=source_subject_id, linkage_confidence="unavailable",
            vista_eligible=False, reason="Valid source exists but access/DUA not approved.")

    if native_same_subject and kind == "valid":
        return CtImagingLinkage(
            status=IMAGING_NATIVE_SAME_SUBJECT, source_dataset=source_dataset,
            source_subject_id=source_subject_id, same_subject_as_clinical_record=True,
            linkage_evidence=[{"method": method, "kind": "Rule A — native same-subject dataset"}],
            linkage_confidence="verified", vista_eligible=True,
            reason="CT and clinical metadata are natively linked in the source dataset.")

    if kind == "valid" and linked_clinical_subject_id and source_subject_id \
            and str(linked_clinical_subject_id) == str(source_subject_id):
        return CtImagingLinkage(
            status=SAME_SUBJECT_VERIFIED, source_dataset=source_dataset,
            source_subject_id=source_subject_id, same_subject_as_clinical_record=True,
            linkage_evidence=[{"method": method, "kind": "Rule B/C — verified source mapping"}],
            linkage_confidence="verified", vista_eligible=True,
            reason="Official/local source mapping verifies same subject.")

    # Real scan, no verified same-subject clinical link -> imaging_only.
    return CtImagingLinkage(
        status=IMAGING_ONLY, source_dataset=source_dataset,
        source_subject_id=source_subject_id, same_subject_as_clinical_record=False,
        linkage_confidence="unavailable", vista_eligible=True,
        reason="Real CT with no verified same-subject clinical record; segmentation-only.")


def assert_fusion_permitted(linkage: dict | CtImagingLinkage) -> tuple[bool, str]:
    """Gate used by the fusion stage + API route. Returns (allowed, message)."""
    status = linkage.get("status") if isinstance(linkage, dict) else linkage.status
    if is_fusion_allowed(status):
        return True, "verified same-subject linkage"
    return False, ("This CT cannot be fused with the clinical case because "
                   "same-subject linkage has not been verified "
                   f"(status={status}).")
