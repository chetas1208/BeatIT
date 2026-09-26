"""Standalone router for the unified BeatIT conversation endpoint (Wave 2).

Not mounted into python/hearttwin/api.py — that integration is a deliberate
follow-up step (see docs/assistant/wave2/conversation-api.md) so a shared
file is touched carefully, once, by whoever wires the real pipeline in.

This module is import-safe and self-testable: `router` is a plain
`fastapi.APIRouter` any test can mount into its own throwaway `FastAPI()` app.
"""

from __future__ import annotations

from fastapi import APIRouter

from python.hearttwin.assistant.schemas import (
    AssistantRequest,
    AssistantResponse,
    AssistantTraceMeta,
    ExecutionClass,
)
from python.hearttwin.safety import DISCLAIMER

router = APIRouter(tags=["assistant"])


def _build_stub_response(request: AssistantRequest) -> AssistantResponse:
    """Deterministic placeholder pipeline.

    EXTENSION POINT: Laya (System-1 decision), the tool registry, and the
    model router don't exist yet — other Wave 2 agents are building them in
    parallel. Once they land, replace the body of this function with:
      decision = laya.decide(request)
      ... dispatch on decision.execution_class ...
    The route handler below stays unchanged; only this function's internals
    change, which is the point of keeping it separate from `post_message`.
    """
    return AssistantResponse(
        message=(
            "The unified BeatIT assistant pipeline is not wired up yet — "
            "this is a Wave 2 schema/router skeleton, not a live decision "
            "path. No tool was called and no clinical content was generated."
        ),
        artifacts=[],
        safety_disclaimer=DISCLAIMER,
        execution_class=ExecutionClass.UNSUPPORTED,
        trace=AssistantTraceMeta(tools_invoked=[]),
    )


@router.post("/message", response_model=AssistantResponse)
async def post_message(request: AssistantRequest) -> AssistantResponse:
    # Pydantic has already validated `request` (incl. the
    # conversation_id/context.conversation_id match) by the time we get here.
    return _build_stub_response(request)
