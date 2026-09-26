"""Optional VISTA-3D adapter boundary.

This adapter validates a local checkpoint and volume contract but does not
pretend to segment data when MONAI/VISTA execution is not explicitly wired.
Callers can inject a framework-specific runner without leaking it into the
rest of BeatIT.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from python.hearttwin.imaging.schemas import SegmentationResult, VolumeInput
from python.hearttwin.models import get_model_registry


class Vista3DSegmenter:
    capability = "medical-segmentation"

    def __init__(self, runner: Callable[[VolumeInput, Path], SegmentationResult] | None = None) -> None:
        self._runner = runner

    def segment_volume(self, volume: VolumeInput) -> SegmentationResult:
        if volume.modality.upper() != "CT":
            return SegmentationResult(
                labels={}, label_map_path=None, source_model="vista3d",
                completed=False, warnings=("VISTA-3D adapter currently accepts CT volumes only",),
            )
        volume_path = Path(volume.path).expanduser()
        if not volume_path.is_file():
            return SegmentationResult(
                labels={}, label_map_path=None, source_model="vista3d",
                completed=False, warnings=("input volume not found",),
            )
        if self._runner is None:
            return SegmentationResult(
                labels={}, label_map_path=None, source_model="vista3d",
                completed=False, warnings=("VISTA-3D runner is not configured; procedural geometry remains available",),
            )
        path = get_model_registry().resolve_model_path(self.capability)
        if path is None or not path.is_file():
            return SegmentationResult(
                labels={}, label_map_path=None, source_model="vista3d",
                completed=False, warnings=("VISTA-3D checkpoint is not available",),
            )
        try:
            return self._runner(volume, path)
        except (OSError, RuntimeError, ValueError):
            return SegmentationResult(
                labels={}, label_map_path=None, source_model="vista3d",
                completed=False, warnings=("VISTA-3D runner failed; procedural geometry remains available",),
            )
