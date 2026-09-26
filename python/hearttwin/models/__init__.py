"""Provider-neutral metadata and lifecycle helpers for local models.

The registry deliberately does not import torch, MONAI, or transformers. A
missing optional model must not prevent the deterministic twin from starting.
"""

from python.hearttwin.models.registry import ModelRegistry, get_model_registry
from python.hearttwin.models.schemas import ModelSpec, ModelStatus

__all__ = ["ModelRegistry", "ModelSpec", "ModelStatus", "get_model_registry"]
