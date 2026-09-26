"""CareGuard's Anthropic integration.

Design mirrors DualBeat's "LLMs never do the math" law: Claude structures
evidence and writes prose, but every clinical number and every deterministic
decision comes from Python. The whole pipeline runs WITHOUT an API key
(deterministic paths); Claude is an optional enhancement layer.

Guarantees enforced here:
  * structured output validated against a JSON Schema before use (no prose→state);
  * Fable ``stop_reason='refusal'`` on HTTP 200 is detected, never treated as
    success — retry on the fallback model, else safe abstention;
  * identifiable data never reaches a deidentify-only model (Fable);
  * raw prompts / raw model reasoning are never logged.
"""

from __future__ import annotations

__all__ = ["client", "model_router", "structured_output", "refusal_handler"]
