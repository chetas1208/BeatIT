"""Conservative, metadata-only identifiability descriptions for M8.

This module does not estimate structural or practical identifiability.  In
particular, it does not calculate a Jacobian rank, Fisher information,
profile likelihood, posterior, or uniqueness claim.  When the supplied
metadata is present, the result is intentionally labelled
``descriptive_only``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

IdentifiabilityStatus = Literal["descriptive_only", "unavailable", "unsupported"]

_SUPPORTED_METHODS = frozenset({"descriptive", "descriptive_only", "metadata"})
_METHOD_KEYS = ("identifiability_method", "analysis_method", "method")
_OUTPUT_LINK_KEYS = ("output_ids", "metric_ids", "outputs")


@dataclass(frozen=True)
class IdentifiabilityAssessment:
    """One conservative status for a parameter and its available outputs."""

    parameter_id: str | None
    status: IdentifiabilityStatus
    related_output_ids: tuple[str, ...]
    available_parameter_fields: tuple[str, ...]
    available_output_fields: tuple[str, ...]
    reason: str
    limitations: tuple[str, ...]


def _record(value: Any) -> dict[str, Any] | None:
    """Convert a metadata object to a shallow mapping without mutating it."""

    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python")
        return dict(dumped) if isinstance(dumped, Mapping) else None
    values = getattr(value, "__dict__", None)
    return dict(values) if isinstance(values, Mapping) else None


def _records(metadata: Any, identifier_key: str) -> tuple[dict[str, Any], ...]:
    """Normalize keyed or sequence metadata while preserving declared IDs."""

    if metadata is None:
        return ()
    if isinstance(metadata, Mapping):
        # A single record is accepted, as are mappings keyed by parameter or
        # metric ID.  The latter is the shape used by lightweight callers.
        if identifier_key in metadata:
            item = _record(metadata)
            return (item,) if item is not None else ()
        normalized: list[dict[str, Any]] = []
        for key, value in metadata.items():
            item = _record(value)
            if item is None:
                continue
            item.setdefault(identifier_key, key)
            normalized.append(item)
        return tuple(normalized)
    if isinstance(metadata, Sequence) and not isinstance(metadata, (str, bytes)):
        result = []
        for value in metadata:
            item = _record(value)
            if item is not None:
                result.append(item)
        return tuple(result)
    if isinstance(metadata, Iterable) and not isinstance(metadata, (str, bytes)):
        result = []
        for value in metadata:
            item = _record(value)
            if item is not None:
                result.append(item)
        return tuple(result)
    return ()


def _identifier(item: Mapping[str, Any], key: str) -> str | None:
    value = item.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _requested_method(*items: Mapping[str, Any]) -> str | None:
    for item in items:
        for key in _METHOD_KEYS:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
    return None


def _linked_output_ids(
    parameter: Mapping[str, Any], output_ids: tuple[str, ...]
) -> tuple[str, ...]:
    for key in _OUTPUT_LINK_KEYS:
        value = parameter.get(key)
        if isinstance(value, str) and value.strip():
            declared = (value.strip(),)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            declared = tuple(
                item.strip() for item in value if isinstance(item, str) and item.strip()
            )
        else:
            continue
        return tuple(item for item in declared if item in output_ids)
    return output_ids


def _assessment(
    parameter: Mapping[str, Any],
    outputs_by_id: Mapping[str, Mapping[str, Any]],
) -> IdentifiabilityAssessment:
    parameter_id = _identifier(parameter, "parameter_id")
    related_ids = _linked_output_ids(parameter, tuple(outputs_by_id))
    related = [outputs_by_id[item] for item in related_ids]
    parameter_fields = tuple(sorted(key for key, value in parameter.items() if value is not None))
    output_fields = tuple(
        sorted({key for output in related for key, value in output.items() if value is not None})
    )
    limitations = (
        "Metadata availability does not establish that a parameter is uniquely learnable.",
        "No structural or practical identifiability estimator is implemented.",
        "This status is not a confidence level, posterior, or clinical inference.",
    )

    if parameter_id is None:
        return IdentifiabilityAssessment(
            parameter_id=None,
            status="unsupported",
            related_output_ids=(),
            available_parameter_fields=parameter_fields,
            available_output_fields=(),
            reason="parameter metadata has no non-empty parameter_id",
            limitations=limitations,
        )

    requested_method = _requested_method(parameter)
    if requested_method is not None and requested_method not in _SUPPORTED_METHODS:
        return IdentifiabilityAssessment(
            parameter_id=parameter_id,
            status="unsupported",
            related_output_ids=related_ids,
            available_parameter_fields=parameter_fields,
            available_output_fields=output_fields,
            reason=f"requested identifiability method is unsupported: {requested_method}",
            limitations=limitations,
        )

    if not outputs_by_id:
        return IdentifiabilityAssessment(
            parameter_id=parameter_id,
            status="unavailable",
            related_output_ids=(),
            available_parameter_fields=parameter_fields,
            available_output_fields=(),
            reason="output metadata is unavailable",
            limitations=limitations,
        )

    if not related_ids:
        return IdentifiabilityAssessment(
            parameter_id=parameter_id,
            status="unavailable",
            related_output_ids=(),
            available_parameter_fields=parameter_fields,
            available_output_fields=(),
            reason="declared parameter-to-output links do not match available output metadata",
            limitations=limitations,
        )

    return IdentifiabilityAssessment(
        parameter_id=parameter_id,
        status="descriptive_only",
        related_output_ids=related_ids,
        available_parameter_fields=parameter_fields,
        available_output_fields=output_fields,
        reason="parameter and output metadata are available for descriptive review only",
        limitations=limitations,
    )


def assess_identifiability(
    parameter_metadata: Any,
    output_metadata: Any = None,
) -> tuple[IdentifiabilityAssessment, ...]:
    """Describe metadata availability without claiming parameter uniqueness.

    ``parameter_metadata`` and ``output_metadata`` may be keyed mappings,
    sequences of records, or M5.5 Pydantic objects.  Passing an ensemble-like
    object as the first argument also works: its ``parameter_distributions``
    and ``distributions`` fields are used when ``output_metadata`` is omitted.

    Empty or malformed metadata is reported as ``unavailable`` or
    ``unsupported`` rather than being treated as evidence of identifiability.
    """

    if output_metadata is None:
        ensemble = parameter_metadata
        if isinstance(ensemble, Mapping):
            parameter_metadata = ensemble.get("parameter_distributions", ensemble)
            output_metadata = ensemble.get("distributions")
        else:
            parameter_metadata = getattr(ensemble, "parameter_distributions", ensemble)
            output_metadata = getattr(ensemble, "distributions", None)

    parameters = _records(parameter_metadata, "parameter_id")
    outputs = _records(output_metadata, "metric_id")
    outputs_by_id = {
        output_id: item
        for item in outputs
        if (output_id := _identifier(item, "metric_id")) is not None
    }

    if not parameters:
        return (
            IdentifiabilityAssessment(
                parameter_id=None,
                status="unavailable",
                related_output_ids=tuple(outputs_by_id),
                available_parameter_fields=(),
                available_output_fields=tuple(
                    sorted({key for item in outputs_by_id.values() for key in item})
                ),
                reason="parameter metadata is unavailable",
                limitations=(
                    "Metadata availability does not establish that a parameter is uniquely learnable.",
                    "No structural or practical identifiability estimator is implemented.",
                ),
            ),
        )

    return tuple(_assessment(parameter, outputs_by_id) for parameter in parameters)


describe_identifiability = assess_identifiability


__all__ = [
    "IdentifiabilityAssessment",
    "IdentifiabilityStatus",
    "assess_identifiability",
    "describe_identifiability",
]
