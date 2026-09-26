"""Framework-neutral volume and segmentation values."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VolumeInput:
    path: str
    modality: str = "CT"
    spacing_mm: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class SegmentationResult:
    labels: dict[int, str]
    label_map_path: str | None
    source_model: str
    completed: bool
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
