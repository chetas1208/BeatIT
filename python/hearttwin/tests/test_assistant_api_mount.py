"""Verify the unified assistant router is mounted on the live FastAPI app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from python.hearttwin.api import app
from python.hearttwin.safety import DISCLAIMER

client = TestClient(app)


def _payload(conversation_id: str = "e2e-conv-1") -> dict:
    return {
        "conversation_id": conversation_id,
        "message": "What is the current EF?",
        "context": {"conversation_id": conversation_id, "audience": "general"},
    }


def test_assistant_message_route_is_mounted_on_live_app() -> None:
    response = client.post("/api/v1/assistant/message", json=_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["safety_disclaimer"] == DISCLAIMER
    assert "execution_class" in body
    assert "trace" in body
