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
    # Wave 6 note: "What is the current EF?" matches no registered tool
    # (TWIN family has none), which used to return "unsupported" directly.
    # Wave 6 routes that same "no tool matched" case through the new MODEL
    # ROUTER (orchestrator.py's module docstring point (g)), whose
    # classify_intent policy gate currently always defers to clarification
    # (laya_policy.py: classify_intent measured 58.6% accuracy, below its own
    # 70% trust threshold) rather than ever risking a real model call on an
    # unreliable route — see test_orchestrator.py's equivalent note for the
    # full explanation.
    assert body["execution_class"] == "clarification_required"
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
    # See test_post_message_stub_response_shape's Wave 6 note above.
    assert r.json()["execution_class"] == "clarification_required"
