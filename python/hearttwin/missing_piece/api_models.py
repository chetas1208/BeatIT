"""HTTP request/response models for the M8 Missing Piece surface."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)

from .contracts import MissingPieceResult

_MAX_IDENTIFIER_LENGTH = 128
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_SENSITIVE_KEY_PARTS = (
    "address",
    "api_key",
    "authorization",
    "cookie",
    "dob",
    "email",
    "mrn",
    "password",
    "patient",
    "phone",
    "secret",
    "ssn",
    "token",
)


def _clean_identifier(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > _MAX_IDENTIFIER_LENGTH:
        raise ValueError(f"{field_name} is too long")
    if _IDENTIFIER_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a safe identifier")
    return value


def _contains_sensitive_key(value: object) -> str | None:
    """Return the first secret/PII-shaped metadata key, if present."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(part in normalized for part in _SENSITIVE_KEY_PARTS):
                return str(key)
            found = _contains_sensitive_key(nested)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _contains_sensitive_key(nested)
            if found is not None:
                return found
    return None


class MissingPieceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    baseline_ensemble_id: StrictStr = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    target_metric: StrictStr = Field(min_length=1, max_length=_MAX_IDENTIFIER_LENGTH)
    target_kind: Literal["baseline_output", "shadow_effect"] = "baseline_output"
    shadow_trial_id: StrictStr | None = Field(default=None, max_length=_MAX_IDENTIFIER_LENGTH)
    available_evidence_types: list[StrictStr] = Field(default_factory=list, max_length=32)

    @field_validator("baseline_ensemble_id", "target_metric")
    @classmethod
    def non_empty(cls, value: str) -> str:
        return _clean_identifier(value, "identifier")

    @field_validator("available_evidence_types")
    @classmethod
    def clean_evidence_types(cls, values: list[str]) -> list[str]:
        cleaned = [_clean_identifier(value, "available evidence type") for value in values]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("available evidence types must be unique")
        return cleaned

    @field_validator("shadow_trial_id")
    @classmethod
    def clean_shadow_trial_id(cls, value: str | None) -> str | None:
        return _clean_identifier(value, "shadow_trial_id") if value is not None else None

    @model_validator(mode="after")
    def require_trial_for_effect(self) -> MissingPieceRequest:
        if self.target_kind == "shadow_effect" and self.shadow_trial_id is None:
            raise ValueError("shadow_effect analysis requires shadow_trial_id")
        if self.target_kind == "baseline_output" and self.shadow_trial_id is not None:
            raise ValueError("shadow_trial_id is only valid for shadow_effect analysis")
        return self


class MissingPieceResponse(MissingPieceResult):
    """Named response alias for OpenAPI readability."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    @model_validator(mode="after")
    def reject_sensitive_metadata(self) -> MissingPieceResponse:
        key = _contains_sensitive_key(self.completeness)
        if key is not None:
            raise ValueError(f"completeness contains forbidden sensitive field: {key}")
        return self


__all__ = ["MissingPieceRequest", "MissingPieceResponse"]
