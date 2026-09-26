"""Amazon Bedrock OpenAI-compatible intelligence substrate."""

from python.hearttwin.intelligence.bedrock.auth import (
    auth_configured,
    authorization_headers,
    bedrock_bearer_token,
    bedrock_openai_base_url,
)
from python.hearttwin.intelligence.bedrock.chat_completions import build_chat_payload, complete_via_chat_completions
from python.hearttwin.intelligence.bedrock.health import bedrock_openai_reachable
from python.hearttwin.intelligence.bedrock.models import ModelRole, get_model_id, model_registry_health
from python.hearttwin.intelligence.bedrock.responses import complete_via_responses, model_supports_responses_api

__all__ = [
    "ModelRole",
    "auth_configured",
    "authorization_headers",
    "bedrock_bearer_token",
    "bedrock_openai_base_url",
    "bedrock_openai_reachable",
    "build_chat_payload",
    "complete_via_chat_completions",
    "complete_via_responses",
    "get_model_id",
    "model_registry_health",
    "model_supports_responses_api",
]
