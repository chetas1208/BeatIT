"""Router stub tests for python/hearttwin/assistant/router.py.

Uses an isolated FastAPI app + TestClient — never imports python.hearttwin.api
— so this stays independent of the live app and of Codex's concurrent,
unrelated shadow_trial_* work in this shared working tree.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from python.hearttwin.assistant.router import router
from python.hearttwin.safety import DISCLAIMER

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


def _valid_payload(conversation_id: str = "conv-1") -> dict:
    return {
        "conversation_id": conversation_id,
        "message": "What is the current EF?",
        "context": {"conversation_id": conversation_id, "audience": "general"},
    }


def test_post_message_stub_response_shape() -> None:
    r = client.post("/message", json=_valid_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["safety_disclaimer"] == DISCLAIMER
    assert body["execution_class"] == "unsupported"
    assert body["artifacts"] == []
    assert "request_id" in body["trace"]


def test_post_message_rejects_mismatched_context_conversation_id() -> None:
    payload = _valid_payload(conversation_id="conv-1")
    payload["context"]["conversation_id"] = "conv-2"
    r = client.post("/message", json=payload)
    assert r.status_code == 422


def test_post_message_rejects_missing_message() -> None:
    payload = _valid_payload()
    del payload["message"]
    r = client.post("/message", json=payload)
    assert r.status_code == 422


def test_post_message_rejects_bad_audience() -> None:
    payload = _valid_payload()
    payload["context"]["audience"] = "nurse"
    r = client.post("/message", json=payload)
    assert r.status_code == 422


def test_post_message_physician_audience_still_stubbed() -> None:
    payload = _valid_payload()
    payload["context"]["audience"] = "physician"
    r = client.post("/message", json=payload)
    assert r.status_code == 200
    assert r.json()["execution_class"] == "unsupported"
