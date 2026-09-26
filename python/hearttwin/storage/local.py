"""Safe local artifact store for development and deterministic tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

from python.hearttwin.storage.base import ArtifactStore


def _safe_path(root: Path, key: str) -> Path:
    candidate = (root / key).resolve()
    if candidate != root.resolve() and root.resolve() not in candidate.parents:
        raise ValueError("artifact key escapes local storage root")
    return candidate


class LocalArtifactStore(ArtifactStore):
    def __init__(self, root: str | Path = "data/artifacts") -> None:
        self.root = Path(root).resolve()

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        del content_type
        path = _safe_path(self.root, key)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(write)

    async def get(self, key: str) -> bytes | None:
        path = _safe_path(self.root, key)
        return await asyncio.to_thread(lambda: path.read_bytes() if path.is_file() else None)

    async def exists(self, key: str) -> bool:
        path = _safe_path(self.root, key)
        return await asyncio.to_thread(path.is_file)
