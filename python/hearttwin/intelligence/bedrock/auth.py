"""Resolve Bedrock OpenAI runtime auth and base URL from environment."""

from __future__ import annotations

import os


def bedrock_bearer_token() -> str:
    return (
        os.environ.get("MODEL_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "").strip()
    )


def bedrock_openai_base_url() -> str:
    return (
        os.environ.get("MODEL_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or os.environ.get("BEDROCK_OPENAI_BASE_URL", "").strip()
    ).rstrip("/")


def auth_configured() -> bool:
    token = bedrock_bearer_token()
    base = bedrock_openai_base_url()
    if not token or not base:
        return False
    if token.startswith("REPLACE_WITH_") or "CHANGE_ME" in token.upper():
        return False
    return True


def authorization_headers() -> dict[str, str]:
    token = bedrock_bearer_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
