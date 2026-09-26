"""Route programmatic case Q&A through the unified assistant orchestrator."""

from __future__ import annotations

import uuid
from typing import Any

from python.hearttwin.assistant.orchestrator import handle_message
from python.hearttwin.assistant.schemas import AssistantRequest, ConversationContext
from python.hearttwin.safety import DISCLAIMER


async def answer_via_unified_orchestrator(
    case_id: str,
    question: str,
    *,
    audience: str = "general",
) -> dict[str, Any]:
    conversation_id = f"copilot-{case_id}"
    request = AssistantRequest(
        conversation_id=conversation_id,
        message=question.strip(),
        context=ConversationContext(
            conversation_id=conversation_id,
            audience="physician" if audience == "physician" else "general",
            patient_id=case_id,
        ),
    )
    response = await handle_message(request)
    return {
        "ok": True,
        "case_id": case_id,
        "question": question.strip(),
        "answer": response.message,
        "execution_class": response.execution_class.value,
        "tools_invoked": response.trace.tools_invoked,
        "model_used": response.trace.model_used,
        "artifacts": [artifact.model_dump(mode="json") for artifact in response.artifacts],
        "safety_disclaimer": response.safety_disclaimer or DISCLAIMER,
        "unified_orchestrator": True,
        "request_id": response.trace.request_id or str(uuid.uuid4()),
    }
