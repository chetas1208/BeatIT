"""Bedrock-runtime health without GET /models (not supported on bedrock-runtime)."""

from __future__ import annotations

import httpx

from python.hearttwin.intelligence.bedrock.auth import auth_configured, authorization_headers, bedrock_openai_base_url
from python.hearttwin.intelligence.bedrock.chat_completions import build_chat_payload
from python.hearttwin.intelligence.bedrock.models import ModelRole, get_model_id


async def bedrock_openai_reachable(*, timeout_seconds: float = 8.0) -> bool:
    """Minimal chat-completions smoke test for the fast registry model."""
    if not auth_configured():
        return False
    model = get_model_id(ModelRole.FAST)
    base = bedrock_openai_base_url()
    url = f"{base}/chat/completions"
    payload = build_chat_payload(
        model=model,
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=4,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, headers=authorization_headers(), json=payload)
            return response.status_code == 200
    except httpx.HTTPError:
        return False
