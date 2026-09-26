"""Standalone router for the unified BeatIT conversation endpoint.

Not mounted into python/hearttwin/api.py — that integration is a deliberate
follow-up step (see docs/assistant/wave2/conversation-api.md) so a shared
file is touched carefully, once, by whoever wires the real pipeline in.

This module is import-safe and self-testable: `router` is a plain
`fastapi.APIRouter` any test can mount into its own throwaway `FastAPI()` app.

Wave 2 left this file with a hardcoded stub response (`_build_stub_response`,
tagged as the pipeline's extension point). Wave 3 built the real pipeline —
`python/hearttwin/assistant/orchestrator.py`'s `handle_message` — wiring
together Laya, the tool registry, the safety validator, and context
resolution; this route now calls it directly instead of returning the stub.
"""

from __future__ import annotations

from fastapi import APIRouter

from python.hearttwin.assistant.orchestrator import handle_message
from python.hearttwin.assistant.schemas import AssistantRequest, AssistantResponse

router = APIRouter(tags=["assistant"])


@router.post("/message", response_model=AssistantResponse)
async def post_message(request: AssistantRequest) -> AssistantResponse:
    # Pydantic has already validated `request` (incl. the
    # conversation_id/context.conversation_id match) by the time we get here.
    return await handle_message(request)
