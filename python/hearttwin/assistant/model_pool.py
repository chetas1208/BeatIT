"""Bedrock model role registry (legacy import path: ``assistant.model_pool``).

NVIDIA Build key pooling was removed. All generative inference uses the canonical
``python.hearttwin.intelligence`` provider (AWS Bedrock OpenAI-compatible API).
"""

from python.hearttwin.intelligence.bedrock.models import ModelRole, get_model_id, model_registry_health

__all__ = ["ModelRole", "get_model_id", "model_registry_health"]
