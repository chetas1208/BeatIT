"""Environment-driven intelligence provider factory."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from python.hearttwin.intelligence.base import IntelligenceProvider
from python.hearttwin.intelligence.errors import ProviderConfigurationError
from python.hearttwin.intelligence.generic_openai import GenericOpenAICompatibleProvider
from python.hearttwin.intelligence.openai_provider import BedrockOpenAIProvider, OpenAIProvider
from python.hearttwin.intelligence.schemas import ChatMessage, ModelRoleHealth, ProviderHealth
from python.hearttwin.tools.model_config import get_fast_model


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().upper()
    return not normalized or normalized.startswith("REPLACE_WITH_") or "CHANGE_ME" in normalized


@dataclass(frozen=True)
class IntelligenceSettings:
    provider: str
    enabled: bool
    protocol: str
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float
    max_retries: int
    openai_enabled: bool
    openai_api_key: str
    openai_model: str

    @classmethod
    def from_env(cls) -> IntelligenceSettings:
        requested_provider = os.environ.get("INTELLIGENCE_PROVIDER")
        generic_configured = all(
            not _is_placeholder(os.environ.get(name, ""))
            for name in ("MODEL_API_KEY", "MODEL_BASE_URL", "MODEL_NAME")
        )
        if requested_provider:
            default_provider = requested_provider
        elif generic_configured:
            default_provider = "generic"
        elif _bool("OPENAI_ENABLED", False) and not _is_placeholder(os.environ.get("OPENAI_API_KEY", "")):
            default_provider = "openai"
        else:
            default_provider = "disabled"
        return cls(
            provider=default_provider.strip().lower(),
            enabled=_bool("MODEL_ENABLED", True),
            protocol=os.environ.get("MODEL_API_PROTOCOL", "openai-compatible").strip().lower(),
            api_key=os.environ.get("MODEL_API_KEY", ""),
            base_url=os.environ.get("MODEL_BASE_URL", ""),
            model=os.environ.get("MODEL_NAME", ""),
            timeout_seconds=float(os.environ.get("MODEL_TIMEOUT_SECONDS", "45")),
            max_retries=int(os.environ.get("MODEL_MAX_RETRIES", "2")),
            openai_enabled=_bool("OPENAI_ENABLED", False),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            # Preserve the application's established model defaults for the
            # legacy first-party OpenAI path. Generic providers remain
            # intentionally strict and must declare MODEL_NAME explicitly.
            openai_model=os.environ.get("OPENAI_MODEL", os.environ.get("OPENAI_MODEL_FAST", get_fast_model())),
        )


class DisabledIntelligenceProvider(IntelligenceProvider):
    name = "disabled"
    protocol = "none"

    async def complete(self, messages, **kwargs):  # type: ignore[no-untyped-def]
        from python.hearttwin.intelligence.errors import ProviderUnavailable

        raise ProviderUnavailable("intelligence provider is disabled")

    async def health(self) -> ProviderHealth:
        return ProviderHealth(enabled=False, protocol="none", reachable=False, model_configured=False, provider=self.name)


def create_intelligence_provider(settings: IntelligenceSettings | None = None) -> IntelligenceProvider:
    config = settings or IntelligenceSettings.from_env()
    if not config.enabled or config.provider == "disabled":
        return DisabledIntelligenceProvider()
    if config.provider in {"openai", "bedrock_openai"}:
        if config.provider == "openai" and not config.openai_enabled:
            raise ProviderConfigurationError("INTELLIGENCE_PROVIDER=openai requires OPENAI_ENABLED=true")
        api_key = (
            config.openai_api_key
            or config.api_key
            or os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
        ).strip()
        model = (config.openai_model or config.model).strip()
        if _is_placeholder(api_key) or _is_placeholder(model):
            raise ProviderConfigurationError("Bedrock OpenAI provider requires bearer token and default model")
        provider_cls = BedrockOpenAIProvider if config.provider == "bedrock_openai" else OpenAIProvider
        return provider_cls(
            api_key=api_key,
            model=model,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
    if config.provider == "generic":
        if config.protocol != "openai-compatible":
            raise ProviderConfigurationError(f"unsupported model protocol: {config.protocol}")
        if any(_is_placeholder(value) for value in (config.api_key, config.base_url, config.model)):
            raise ProviderConfigurationError("generic provider requires real MODEL_API_KEY, MODEL_BASE_URL, and MODEL_NAME values")
        return GenericOpenAICompatibleProvider(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
    raise ProviderConfigurationError(f"unsupported intelligence provider: {config.provider}")


def configured_provider_or_disabled() -> IntelligenceProvider:
    """Return a safe provider without making startup fail on missing config."""
    try:
        return create_intelligence_provider()
    except (ProviderConfigurationError, ValueError):
        return DisabledIntelligenceProvider()


def provider_available() -> bool:
    return not isinstance(configured_provider_or_disabled(), DisabledIntelligenceProvider)


async def complete_text(
    messages: Sequence[ChatMessage | Mapping[str, Any]],
    *,
    model: str | None = None,
    response_format: Mapping[str, Any] | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    timeout_seconds: float | None = None,
    extra: Mapping[str, Any] | None = None,
) -> str:
    """Shared low-level seam used by legacy agents during provider migration."""
    provider = configured_provider_or_disabled()
    # Legacy agents still pass OPENAI_MODEL_* selections. Generic and Bedrock paths
    # honor explicit per-call model IDs from the registry/router.
    effective_model = None if provider.name == "generic" else model
    response = await provider.complete(
        messages,
        model=effective_model,
        response_format=response_format,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        extra=extra,
    )
    return response.content


async def intelligence_status() -> ProviderHealth:
    from python.hearttwin.intelligence.bedrock.models import ModelRole, get_model_id

    provider = configured_provider_or_disabled()
    config = IntelligenceSettings.from_env()
    base = await provider.health()

    def _role(role: ModelRole) -> ModelRoleHealth:
        env_name = {
            ModelRole.FAST: "MODEL_FAST",
            ModelRole.BALANCED: "MODEL_BALANCED",
            ModelRole.DEEP: "MODEL_DEEP",
            ModelRole.SAFETY: "MODEL_SAFETY",
        }[role]
        raw = os.environ.get(env_name, "").strip()
        configured = bool(raw and not _is_placeholder(raw))
        return ModelRoleHealth(model_id=get_model_id(role), configured=configured)

    role_update = {
        "fast": _role(ModelRole.FAST),
        "balanced": _role(ModelRole.BALANCED),
        "deep": _role(ModelRole.DEEP),
        "safety": _role(ModelRole.SAFETY),
    }
    if isinstance(provider, DisabledIntelligenceProvider):
        return base.model_copy(update=role_update)
    return base.model_copy(
        update={
            "protocol": config.protocol or base.protocol,
            **role_update,
        }
    )
