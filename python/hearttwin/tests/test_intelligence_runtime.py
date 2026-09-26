"""Unit tests for the provider-neutral runtime and artifact storage."""

from __future__ import annotations

import httpx
import pytest

from python.hearttwin.intelligence.errors import ProviderConfigurationError
from python.hearttwin.intelligence.factory import (
    DisabledIntelligenceProvider,
    configured_provider_or_disabled,
    create_intelligence_provider,
)
from python.hearttwin.intelligence.generic_openai import GenericOpenAICompatibleProvider
from python.hearttwin.storage.local import LocalArtifactStore
from python.hearttwin.storage.s3 import S3ArtifactStore
from python.hearttwin.tools.storage import get_file, store_file


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers = {"x-request-id": "request-test"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("failed", request=httpx.Request("POST", "http://test"), response=httpx.Response(self.status_code))

    def json(self) -> dict:
        return self._payload


class FakeHTTPClient:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict, dict]] = []

    async def post(self, url: str, *, headers: dict, json: dict) -> FakeResponse:
        self.posts.append((url, headers, json))
        return FakeResponse({"model": json["model"], "choices": [{"message": {"content": '{"ok": true}'}}]})

    async def get(self, url: str, *, headers: dict) -> FakeResponse:
        del url, headers
        return FakeResponse({"data": []})


class FlakyHTTPClient(FakeHTTPClient):
    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    async def post(self, url: str, *, headers: dict, json: dict) -> FakeResponse:
        self.attempts += 1
        if self.attempts == 1:
            raise httpx.ConnectError("temporary provider failure")
        return FakeResponse(
            {
                "model": json["model"],
                "choices": [{"message": {"content": '{"evidence": [{"type": "heart_rate", "value": 72, "unit": "bpm", "confidence": 0.9}]}'}}],
            }
        )


@pytest.mark.asyncio
async def test_generic_provider_uses_configured_endpoint_and_auth() -> None:
    client = FakeHTTPClient()
    provider = GenericOpenAICompatibleProvider(
        api_key="fake-key",
        base_url="https://model.example/v1",
        model="demo-model",
        client=client,  # type: ignore[arg-type]
    )
    result = await provider.complete([{"role": "user", "content": "hello"}], response_format={"type": "json_object"})
    assert result.content == '{"ok": true}'
    assert client.posts[0][0] == "https://model.example/v1/chat/completions"
    assert client.posts[0][1]["Authorization"] == "Bearer fake-key"
    assert client.posts[0][2]["model"] == "demo-model"

    await provider.complete([{"role": "user", "content": "hello"}], extra={"max_completion_tokens": 7})
    assert client.posts[1][2]["max_completion_tokens"] == 7
    assert "max_tokens" not in client.posts[1][2]


@pytest.mark.asyncio
async def test_generic_provider_retries_and_parses_typed_evidence() -> None:
    client = FlakyHTTPClient()
    provider = GenericOpenAICompatibleProvider(
        api_key="fake-key",
        base_url="https://model.example/v1",
        model="demo-model",
        max_retries=1,
        client=client,  # type: ignore[arg-type]
    )
    candidates = await provider.extract_clinical_evidence(
        "Heart rate 72 bpm",
        {"source": "manual", "case_id": "case-test"},
    )
    assert client.attempts == 2
    assert candidates[0].type == "heart_rate"
    assert candidates[0].value == 72
    assert candidates[0].confidence == 0.9


def test_factory_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "disabled")
    assert isinstance(create_intelligence_provider(), DisabledIntelligenceProvider)

    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "generic")
    monkeypatch.setenv("MODEL_API_KEY", "fake-key")
    monkeypatch.setenv("MODEL_BASE_URL", "http://localhost:9000/v1")
    monkeypatch.setenv("MODEL_NAME", "demo")
    assert isinstance(create_intelligence_provider(), GenericOpenAICompatibleProvider)

    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "invalid")
    with pytest.raises(ProviderConfigurationError):
        create_intelligence_provider()


def test_incomplete_provider_configuration_falls_back_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "generic")
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert isinstance(configured_provider_or_disabled(), DisabledIntelligenceProvider)


def test_openai_is_not_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    with pytest.raises(ProviderConfigurationError):
        create_intelligence_provider()


def test_placeholder_generic_configuration_is_disabled_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "generic")
    monkeypatch.setenv("MODEL_API_KEY", "REPLACE_WITH_MODEL_API_KEY")
    monkeypatch.setenv("MODEL_BASE_URL", "http://localhost:9000/v1")
    monkeypatch.setenv("MODEL_NAME", "REPLACE_WITH_MODEL_NAME")
    assert isinstance(configured_provider_or_disabled(), DisabledIntelligenceProvider)


@pytest.mark.asyncio
async def test_local_artifact_store_put_get_exists(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalArtifactStore(tmp_path)
    await store.put("case/file.txt", b"hello", content_type="text/plain")
    assert await store.exists("case/file.txt")
    assert await store.get("case/file.txt") == b"hello"
    assert await store.get("missing") is None
    with pytest.raises(ValueError):
        await store.put("../escape", b"no")


@pytest.mark.asyncio
async def test_s3_store_uses_injected_client() -> None:
    class Body:
        def read(self) -> bytes:
            return b"stored"

    class Client:
        def put_object(self, **kwargs):
            assert kwargs["Bucket"] == "bucket"

        def get_object(self, **kwargs):
            return {"Body": Body()}

        def head_object(self, **kwargs):
            return {}

    store = S3ArtifactStore(bucket="bucket", region="us-west-2", client=Client())
    await store.put("a", b"b")
    assert await store.get("a") == b"stored"
    assert await store.exists("a")


@pytest.mark.asyncio
async def test_application_file_storage_uses_local_artifact_store_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)
    monkeypatch.setenv("AWS_ENABLED", "false")
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path))
    file_id, storage_url = await store_file(b"payload", "evidence.txt", "text/plain")
    assert storage_url is None
    assert await get_file(file_id) == b"payload"


def test_s3_store_requires_configuration() -> None:
    with pytest.raises(ValueError):
        S3ArtifactStore(bucket="", region="us-west-2")
