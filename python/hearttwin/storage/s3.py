"""Optional AWS S3 artifact store.

`boto3` is deliberately optional. Local development never imports or requires
it; AWS is selected only when AWS_ENABLED=true and a bucket is configured.
"""

from __future__ import annotations

import asyncio
from typing import Any

from python.hearttwin.storage.base import ArtifactStore


class S3ArtifactStore(ArtifactStore):
    def __init__(self, *, bucket: str, region: str, client: Any | None = None) -> None:
        if not bucket.strip() or not region.strip():
            raise ValueError("S3 storage requires AWS_S3_BUCKET and AWS_REGION")
        self.bucket = bucket
        self.region = region
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("AWS S3 storage requires the optional boto3 dependency") from exc
        return boto3.client("s3", region_name=self.region)

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        kwargs: dict[str, Any] = {"Bucket": self.bucket, "Key": key, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        await asyncio.to_thread(self._get_client().put_object, **kwargs)

    async def get(self, key: str) -> bytes | None:
        def read() -> bytes | None:
            try:
                return self._get_client().get_object(Bucket=self.bucket, Key=key)["Body"].read()
            except Exception as exc:  # boto's typed ClientError is optional here
                if getattr(exc, "response", {}).get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                    return None
                raise

        return await asyncio.to_thread(read)

    async def exists(self, key: str) -> bool:
        def check() -> bool:
            try:
                self._get_client().head_object(Bucket=self.bucket, Key=key)
                return True
            except Exception as exc:
                if getattr(exc, "response", {}).get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                    return False
                raise

        return await asyncio.to_thread(check)
