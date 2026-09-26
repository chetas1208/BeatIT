"""Provider-neutral artifact storage contract."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ArtifactStore(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        """Store bytes under a caller-owned relative key."""

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """Return bytes or None when the object does not exist."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Return whether an artifact exists."""
