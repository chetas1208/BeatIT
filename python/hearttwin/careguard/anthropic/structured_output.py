"""Structured-output enforcement: force a tool call whose input_schema IS the
JSON Schema, then validate the returned object against a Pydantic model.

This is version-robust across Anthropic SDK releases: instead of relying on a
specific ``response_format``/``output_config`` field, CareGuard defines a single
forced tool ``emit_structured_output`` and reads its validated ``input``.
"""

from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel, ValidationError

STRUCTURED_TOOL_NAME = "emit_structured_output"


def build_forced_tool(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": STRUCTURED_TOOL_NAME,
        "description": "Return the analysis strictly matching the provided JSON Schema.",
        "input_schema": schema,
    }


def extract_tool_input(response: Any) -> dict[str, Any] | None:
    """Pull the emit_structured_output tool input from a Messages response."""
    content = getattr(response, "content", None)
    if content is None and isinstance(response, dict):
        content = response.get("content")
    for block in content or []:
        btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
        if btype == "tool_use":
            name = getattr(block, "name", None) or (block.get("name") if isinstance(block, dict) else None)
            if name == STRUCTURED_TOOL_NAME:
                return getattr(block, "input", None) or (block.get("input") if isinstance(block, dict) else None)
    return None


def validate(model_cls: Type[BaseModel], data: dict[str, Any]) -> BaseModel:
    """Validate; raises ValidationError on malformed output (never coerce prose)."""
    return model_cls.model_validate(data)


def try_validate(model_cls: Type[BaseModel], data: Any) -> tuple[BaseModel | None, str | None]:
    if not isinstance(data, dict):
        return None, "model output was not a JSON object"
    try:
        return validate(model_cls, data), None
    except ValidationError as exc:
        return None, f"structured output failed schema validation: {exc.error_count()} error(s)"
