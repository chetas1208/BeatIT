"""Provider-neutral intelligence contract.

The cardiac engine owns all numerical physiology. Providers only produce
language or untrusted extraction candidates from explicitly supplied context.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

from python.hearttwin.intelligence.schemas import (
    ChatMessage,
    ClinicalEvidenceCandidate,
    ProviderHealth,
    ProviderResponse,
)


class IntelligenceProvider(ABC):
    """Minimal transport plus safe domain-level convenience methods."""

    name: str = "unknown"
    protocol: str = "openai-compatible"

    @abstractmethod
    async def complete(
        self,
        messages: Sequence[ChatMessage | Mapping[str, Any]],
        *,
        model: str | None = None,
        response_format: Mapping[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout_seconds: float | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        """Return provider text for a caller-supplied, provenance-bound prompt."""

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Return safe runtime status without exposing configuration secrets."""

    async def extract_clinical_evidence(
        self,
        evidence_text: str,
        provenance: Mapping[str, Any],
        *,
        model: str | None = None,
    ) -> list[ClinicalEvidenceCandidate]:
        response = await self.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "Extract candidate cardiac evidence only from the supplied text. "
                        "Return a JSON object with an evidence array. Never infer absent values."
                    ),
                ),
                ChatMessage(
                    role="user",
                    content={"text": evidence_text, "provenance": dict(provenance)},
                ),
            ],
            model=model,
            response_format={"type": "json_object"},
        )
        import json

        payload = json.loads(response.content)
        candidates = payload.get("evidence", []) if isinstance(payload, dict) else []
        return [ClinicalEvidenceCandidate.model_validate(item) for item in candidates]

    async def explain_component(
        self,
        component: str,
        state: Mapping[str, Any],
        provenance: Sequence[Mapping[str, Any]],
        *,
        model: str | None = None,
    ) -> str:
        return await self._grounded_narrative(
            "Explain the selected cardiac component for education only.",
            {"component": component, "state": dict(state), "provenance": list(provenance)},
            model=model,
        )

    async def summarize_longitudinal_change(
        self,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
        provenance: Sequence[Mapping[str, Any]],
        *,
        model: str | None = None,
    ) -> str:
        return await self._grounded_narrative(
            "Summarize observed longitudinal change without diagnosis or treatment advice.",
            {"before": dict(before), "after": dict(after), "provenance": list(provenance)},
            model=model,
        )

    async def answer_twin_question(
        self,
        question: str,
        state: Mapping[str, Any],
        provenance: Sequence[Mapping[str, Any]],
        *,
        model: str | None = None,
    ) -> str:
        return await self._grounded_narrative(
            "Answer the user's question using only the supplied educational twin state.",
            {"question": question, "state": dict(state), "provenance": list(provenance)},
            model=model,
        )

    async def explain_simulation_result(
        self,
        result: Mapping[str, Any],
        provenance: Sequence[Mapping[str, Any]],
        *,
        model: str | None = None,
    ) -> str:
        return await self._grounded_narrative(
            "Explain deterministic cardiac simulation output without changing any values.",
            {"result": dict(result), "provenance": list(provenance)},
            model=model,
        )

    async def _grounded_narrative(
        self,
        instruction: str,
        context: Mapping[str, Any],
        *,
        model: str | None,
    ) -> str:
        response = await self.complete(
            [
                ChatMessage(role="system", content=instruction),
                ChatMessage(role="user", content=context),
            ],
            model=model,
        )
        return response.content.strip()
