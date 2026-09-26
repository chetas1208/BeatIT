"""Thin re-export of CareGuard's deidentification for the anthropic package."""

from __future__ import annotations

from python.hearttwin.careguard.security import (  # noqa: F401
    assert_no_identifiers,
    deidentify_for_model,
    redact_structured,
    redact_text,
)

__all__ = ["deidentify_for_model", "assert_no_identifiers", "redact_structured", "redact_text"]
