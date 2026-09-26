"""Pydantic schemas for the CT imaging + VISTA extension (spec §12/§14/§17)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

VISTA_LABEL = "Model-derived research segmentation requiring clinician review."
IMAGING_ASSERTION_TYPE = "model_derived_imaging_measurement"


class EndpointCapabilities(BaseModel):
    """Normalized capability handshake (spec §12)."""
    service: Literal["vista3d", "nv-segment-ct", "nv-segment-ctmr", "unknown"] = "unknown"
    version: str = ""
    supported_modalities: list[str] = Field(default_factory=list)
    supported_classes: list[str] = Field(default_factory=list)
    input_formats: list[str] = Field(default_factory=list)
    maximum_upload_bytes: Optional[int] = None
    supports_signed_urls: bool = False
    supports_batch: bool = False
    supports_async_jobs: bool = False
    returns_confidence: bool = False
    returns_masks: bool = True
    returns_measurements: bool = False
    reachable: bool = False
    source: str = "static_fallback"   # live | static_fallback | unavailable
    warnings: list[str] = Field(default_factory=list)


class VistaSegmentationJob(BaseModel):
    """A single segmentation job (spec §14)."""
    job_id: str
    imaging_case_id: str
    source_dataset: str
    source_subject_id: str
    input_uri: str
    input_sha256: str
    modality: Literal["CT", "MR"]
    requested_classes: list[str]
    endpoint_model: str
    endpoint_version: str
    created_at: str
    linkage_status: str
    deidentified: bool
    # runtime state (spec §16)
    state: Literal["queued", "uploading", "submitted", "running", "completed",
                   "completed_with_warning", "failed", "timed_out", "invalid_output",
                   "unsupported"] = "queued"
    accepted_classes: list[str] = Field(default_factory=list)
    rejected_classes: list[str] = Field(default_factory=list)
    submitted_at: Optional[str] = None
    completed_at: Optional[str] = None
    latency_seconds: Optional[float] = None
    retry_count: int = 0
    response_status: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)
    failure_reason: Optional[str] = None
    output_paths: dict = Field(default_factory=dict)


class VistaStructureResult(BaseModel):
    """Per-structure segmentation outcome (spec §17)."""
    structure_id: str
    requested_label: str
    endpoint_label: str
    status: Literal["segmented", "not_found", "unsupported", "failed"]
    mask_uri: Optional[str] = None
    mask_sha256: Optional[str] = None
    voxel_count: Optional[int] = None
    volume_ml: Optional[float] = None
    bounding_box_voxels: Optional[list[int]] = None
    centroid_world_mm: Optional[list[float]] = None
    confidence: Optional[float] = None   # only if endpoint returns a defined measure
    warnings: list[str] = Field(default_factory=list)
    label: str = VISTA_LABEL


class ReferenceMetric(BaseModel):
    """One structure's reference-mask comparison (spec §19)."""
    structure: str
    source_label: str
    vista_label: str
    comparison_allowed: bool
    dice: Optional[float] = None
    jaccard: Optional[float] = None
    sensitivity: Optional[float] = None
    precision: Optional[float] = None
    hd95_mm: Optional[float] = None
    assd_mm: Optional[float] = None
    abs_volume_error_ml: Optional[float] = None
    rel_volume_error: Optional[float] = None
    status: str = "not_computed"
    reason: str = ""
