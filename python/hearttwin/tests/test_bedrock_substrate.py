"""Bedrock substrate unit tests (Wave 2 gate)."""

from __future__ import annotations

import pytest

from python.hearttwin.intelligence.bedrock.auth import auth_configured, bedrock_bearer_token
from python.hearttwin.intelligence.bedrock.responses import (
    model_supports_responses_api,
    parse_responses_content,
)
from python.hearttwin.intelligence.openai_provider import BedrockOpenAIProvider
from python.hearttwin.intelligence.factory import create_intelligence_provider


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


class RouteClient:
    def __init__(self) -> None:
        self.urls: list[str] = []

    async def post(self, url: str, *, headers: dict, json: dict) -> FakeResponse:
        self.urls.append(url)
        if url.endswith("/responses"):
            return FakeResponse({"model": json["model"], "output_text": "via-responses"})
        return FakeResponse({"model": json["model"], "choices": [{"message": {"content": "via-chat"}}]})


@pytest.mark.asyncio
async def test_complete_via_chat_completions_parses_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BASE_URL", "https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1")
    monkeypatch.setenv("MODEL_API_KEY", "token")
    client = RouteClient()
    from python.hearttwin.intelligence.bedrock.chat_completions import complete_via_chat_completions

    content, model = await complete_via_chat_completions(
        model="global.openai.gpt-5.6-luna",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=8,
        client=client,  # type: ignore[arg-type]
    )
    assert content == "via-chat"
    assert model == "global.openai.gpt-5.6-luna"
    assert client.urls[0].endswith("/chat/completions")


def test_auth_configured_rejects_placeholders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_API_KEY", "REPLACE_WITH_BEDROCK_BEARER")
    monkeypatch.setenv("MODEL_BASE_URL", "https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1")
    assert auth_configured() is False
    monkeypatch.setenv("MODEL_API_KEY", "bedrock-bearer-test")
    assert auth_configured() is True
    assert bedrock_bearer_token() == "bedrock-bearer-test"


def test_model_supports_responses_api() -> None:
    assert model_supports_responses_api("global.openai.gpt-5.6-luna") is True
    assert model_supports_responses_api("openai.gpt-oss-20b-1:0") is False


def test_parse_responses_content_variants() -> None:
    assert parse_responses_content({"output_text": "hello"}) == "hello"
    assert (
        parse_responses_content(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "nested"}],
                    }
                ]
            }
        )
        == "nested"
    )


@pytest.mark.asyncio
async def test_bedrock_provider_routes_responses_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_API_PROTOCOL", "responses")
    calls: list[str] = []

    async def fake_responses(**kwargs):  # type: ignore[no-untyped-def]
        calls.append("responses")
        return "via-responses", kwargs["model"]

    monkeypatch.setattr(
        "python.hearttwin.intelligence.bedrock.responses.complete_via_responses",
        fake_responses,
    )
    provider = BedrockOpenAIProvider(api_key="token", model="global.openai.gpt-5.6-luna")
    result = await provider.complete([{"role": "user", "content": "hi"}])
    assert result.content == "via-responses"
    assert calls == ["responses"]


@pytest.mark.asyncio
async def test_bedrock_provider_uses_chat_for_oss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_API_PROTOCOL", "responses")
    calls: list[str] = []

    async def fake_chat(**kwargs):  # type: ignore[no-untyped-def]
        calls.append("chat")
        return "via-chat", kwargs["model"]

    monkeypatch.setattr(
        "python.hearttwin.intelligence.bedrock.chat_completions.complete_via_chat_completions",
        fake_chat,
    )
    provider = BedrockOpenAIProvider(api_key="token", model="openai.gpt-oss-20b-1:0")
    result = await provider.complete([{"role": "user", "content": "hi"}], model="openai.gpt-oss-20b-1:0")
    assert result.content == "via-chat"
    assert calls == ["chat"]


def test_factory_creates_bedrock_openai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "bedrock_openai")
    monkeypatch.setenv("MODEL_ENABLED", "true")
    monkeypatch.setenv("MODEL_API_KEY", "bedrock-token")
    monkeypatch.setenv("MODEL_NAME", "global.openai.gpt-5.6-terra")
    monkeypatch.setenv("OPENAI_API_KEY", "bedrock-token")
    provider = create_intelligence_provider()
    assert provider.name == "bedrock_openai"


def test_python_tree_has_no_nvidia_inference() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    forbidden = (
        "nv" + "api",
        "integrate.api.nvidia",
        "Nemotron",
        "ModelKeyPool",
    )
    for pattern in forbidden:
        hits = [path for path in root.glob("**/*.py") if "tests" not in path.parts]
        matches = [path for path in hits if pattern in path.read_text(encoding="utf-8", errors="ignore")]
        assert not matches, f"found {pattern} in {[str(m.relative_to(root)) for m in matches]}"
