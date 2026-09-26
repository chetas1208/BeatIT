"""Typed boundaries for provider requests and model candidates."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant", "developer"]
    content: Any


class ProviderResponse(BaseModel):
    content: str
    model: str
    provider: str
    request_id: str | None = None
    raw: dict[str, Any] | None = None


class ClinicalEvidenceCandidate(BaseModel):
    """Untrusted extraction output; validators decide whether it enters state."""

    type: str
    value: str | float | None = None
    unit: str | None = None
    source_span: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class ProviderHealth(BaseModel):
    enabled: bool
    protocol: str
    reachable: bool
    model_configured: bool
    provider: str
