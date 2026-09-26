"""Segmentation-to-heart mapping seam.

Raw model label ids stay isolated here; UI components consume semantic names.
"""

from __future__ import annotations

VISTA3D_HEART_LABELS: dict[int, str] = {
    115: "heart",
    6: "aorta",
    7: "inferior_vena_cava",
    119: "pulmonary_vein",
    125: "superior_vena_cava",
}


def map_segmentation_labels(labels: dict[int, str] | None = None) -> dict[int, str]:
    """Return a copy of the configured semantic mapping for downstream use."""
    return dict(labels or VISTA3D_HEART_LABELS)
