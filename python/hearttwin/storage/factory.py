"""Environment-driven artifact-store factory."""

from __future__ import annotations

import os

from python.hearttwin.storage.base import ArtifactStore
from python.hearttwin.storage.local import LocalArtifactStore
from python.hearttwin.storage.s3 import S3ArtifactStore


def _enabled() -> bool:
    return os.environ.get("AWS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def create_artifact_store() -> ArtifactStore:
    if _enabled():
        return S3ArtifactStore(
            bucket=os.environ.get("AWS_S3_BUCKET", ""),
            region=os.environ.get("AWS_REGION", "us-west-2"),
        )
    return LocalArtifactStore(os.environ.get("ARTIFACT_ROOT", "data/artifacts"))


def storage_status() -> dict[str, object]:
    enabled = _enabled()
    configured = bool(os.environ.get("AWS_S3_BUCKET")) if enabled else True
    return {
        "provider": "s3" if enabled else "local",
        "enabled": enabled,
        "configured": configured,
    }
