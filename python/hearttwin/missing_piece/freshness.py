"""Deterministic, descriptive freshness metadata for M8 evidence.

Freshness is a configurable recency display policy. It is not a clinical
validity, reliability, or expiration judgement. Callers must provide the
reference date and the modality/configuration-specific half-life explicitly so
the result can be replayed and audited.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from typing import Any

_SECONDS_PER_DAY = 86_400.0
_HALF_LIFE_METHOD = "exponential_recency_by_explicit_half_life_v1"
_DateLike = date | datetime | str


def _parse_timestamp(value: _DateLike) -> datetime | None:
    """Parse a date or ISO timestamp without guessing a local timezone."""

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(text)
        except ValueError:
            return None
        return datetime(
            parsed_date.year,
            parsed_date.month,
            parsed_date.day,
            tzinfo=UTC,
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        # ``datetime.fromisoformat`` accepts date-only strings as naive
        # midnight; date-only provenance is explicitly interpreted as UTC.
        if len(text) == 10:
            try:
                parsed_date = date.fromisoformat(text)
            except ValueError:
                return None
            return datetime(
                parsed_date.year,
                parsed_date.month,
                parsed_date.day,
                tzinfo=UTC,
            )
        return None
    return parsed.astimezone(UTC)


def _unavailable(
    *,
    observed_at: _DateLike | None,
    reference_at: _DateLike | None,
    half_life_days: float | None,
    modality: str | None,
    reason: str,
) -> dict[str, Any]:
    """Build the stable shape used for all unavailable freshness results."""

    return {
        "available": False,
        "score": None,
        "observed_at": (
            observed_at.isoformat()
            if isinstance(observed_at, (date, datetime))
            else observed_at
        ),
        "reference_at": (
            reference_at.isoformat()
            if isinstance(reference_at, (date, datetime))
            else reference_at
        ),
        "age_days": None,
        "half_life_days": half_life_days,
        "modality": modality,
        "method": _HALF_LIFE_METHOD,
        "reason": reason,
    }


def freshness_metadata(
    observed_at: _DateLike | None,
    *,
    reference_at: _DateLike | None,
    half_life_days: float | None,
    modality: str | None = None,
) -> dict[str, Any]:
    """Return deterministic recency metadata using an explicit half-life.

    ``observed_at`` and ``reference_at`` may be timezone-aware ISO timestamps
    or calendar dates. A timezone-less datetime/string is unavailable rather
    than being interpreted in the machine's local timezone. ``half_life_days``
    is the caller's display policy: at one half-life the score is ``0.5`` and
    at zero age it is ``1.0``. Missing or invalid inputs remain unavailable;
    they are never converted to zero.
    """

    parsed_observed = _parse_timestamp(observed_at) if observed_at is not None else None
    parsed_reference = _parse_timestamp(reference_at) if reference_at is not None else None

    if parsed_observed is None:
        return _unavailable(
            observed_at=observed_at,
            reference_at=reference_at,
            half_life_days=half_life_days,
            modality=modality,
            reason="observed_at is missing or not an explicit date/time",
        )
    if parsed_reference is None:
        return _unavailable(
            observed_at=observed_at,
            reference_at=reference_at,
            half_life_days=half_life_days,
            modality=modality,
            reason="reference_at is missing or not an explicit date/time",
        )
    if not isinstance(half_life_days, (int, float)) or not math.isfinite(float(half_life_days)):
        return _unavailable(
            observed_at=observed_at,
            reference_at=reference_at,
            half_life_days=half_life_days,
            modality=modality,
            reason="half_life_days must be finite",
        )
    if half_life_days <= 0:
        return _unavailable(
            observed_at=observed_at,
            reference_at=reference_at,
            half_life_days=float(half_life_days),
            modality=modality,
            reason="half_life_days must be greater than zero",
        )

    age_days = (parsed_reference - parsed_observed).total_seconds() / _SECONDS_PER_DAY
    if age_days < 0:
        return _unavailable(
            observed_at=observed_at,
            reference_at=reference_at,
            half_life_days=float(half_life_days),
            modality=modality,
            reason="observed_at occurs after reference_at",
        )

    score = math.pow(0.5, age_days / float(half_life_days))
    return {
        "available": True,
        "score": score,
        "observed_at": parsed_observed.isoformat(),
        "reference_at": parsed_reference.isoformat(),
        "age_days": age_days,
        "half_life_days": float(half_life_days),
        "modality": modality,
        "method": _HALF_LIFE_METHOD,
        "reason": None,
    }


def freshness_score(
    observed_at: _DateLike | None,
    *,
    now: _DateLike | None = None,
    half_life_days: float | None = None,
) -> float | None:
    """Return only the deterministic score, or ``None`` when unavailable.

    This compatibility wrapper deliberately has no live-clock fallback. Use
    ``freshness_metadata`` when the audit-visible dates and policy are needed.
    """

    metadata = freshness_metadata(
        observed_at,
        reference_at=now,
        half_life_days=half_life_days,
    )
    return metadata["score"] if metadata["available"] else None


__all__ = ["freshness_metadata", "freshness_score"]
