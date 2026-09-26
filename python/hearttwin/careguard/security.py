"""CareGuard security: deidentification, redaction, and secret hygiene.

Two guarantees this module enforces:

1. **No identifiable patient data reaches a model that must not receive it.**
   ``deidentify_for_model`` strips names/addresses/phones/emails/MRNs/DOBs and
   converts exact dates to relative clinical intervals, leaving only opaque
   internal IDs plus the minimum structured facts.

2. **No secret or raw PHI leaks into logs/traces.** ``redact_text`` extends
   DualBeat's existing ``redact_pii`` and ``safe_config_view`` guarantees the
   public config endpoint returns booleans, never secret values.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from python.hearttwin.safety import redact_pii as _hearttwin_redact_pii

# Keys that must never survive into a model payload or a log line.
_IDENTIFIER_KEYS = {
    "name", "family", "given", "prefix", "suffix", "text",
    "address", "line", "city", "district", "state", "postalcode", "postal_code", "country",
    "telecom", "phone", "email", "contact",
    "birthdate", "birth_date", "dob", "date_of_birth",
    "mrn", "medical_record_number", "ssn", "identifier", "photo",
    "maidenname", "mothersmaidenname",
}

# Keys that are safe structured clinical facts (allow-list for model payloads).
_CLINICAL_ALLOW_KEYS = {
    "resource_type", "resourcetype", "category", "code", "code_system", "coding",
    "system", "display", "value", "unit", "status", "severity", "class",
    "rxcui", "loinc", "snomed", "icd", "interpretation", "reference_range",
    "fact_id", "resource_id", "assertion_type", "confidence", "clinical_interval",
    "relative_day", "onset_interval", "medication", "condition", "observation",
    "allergy", "problem", "comorbidity", "lab", "vital",
}

_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_LONG_ID = re.compile(r"\b\d{7,}\b")
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?\b")


def opaque_id(*parts: str) -> str:
    """Deterministic opaque resource id — stable within a case, non-identifying."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return f"cg-{digest[:16]}"


def redact_text(text: str) -> str:
    """Redact PHI/PII from a free-text string for logs/traces.

    Builds on DualBeat's ``redact_pii`` (SSN/email/id/date) and adds phone
    numbers. Never raises; returns a redacted copy.
    """
    if not text:
        return text
    out = _hearttwin_redact_pii(str(text))
    out = _PHONE.sub("[PHONE-REDACTED]", out)
    return out


def _relative_interval(_raw_date: str) -> str:
    """Collapse an exact date to a non-identifying relative marker.

    We deliberately do NOT compute an offset from today (that would require a
    reference clock and could still narrow identity); we emit a coarse marker so
    downstream reasoning stays date-free.
    """
    return "[relative-clinical-interval]"


def deidentify_for_model(obj: Any, *, drop_identifiers: bool = True) -> Any:
    """Return a deep, deidentified copy safe to send to a model.

    - Drops identifier-bearing keys entirely.
    - Converts ISO dates to a relative-interval marker.
    - Redacts PHI patterns inside any surviving strings.
    - Leaves structured clinical facts (codes, values, units, status) intact.
    """
    if isinstance(obj, dict):
        clean: dict[str, Any] = {}
        for key, val in obj.items():
            klow = str(key).lower().replace("-", "").replace("_", "")
            if drop_identifiers and klow in {k.replace("_", "") for k in _IDENTIFIER_KEYS}:
                continue
            clean[key] = deidentify_for_model(val, drop_identifiers=drop_identifiers)
        return clean
    if isinstance(obj, (list, tuple)):
        return [deidentify_for_model(v, drop_identifiers=drop_identifiers) for v in obj]
    if isinstance(obj, str):
        s = _ISO_DATE.sub(_relative_interval(obj), obj)
        s = _SSN.sub("[SSN-REDACTED]", s)
        s = _EMAIL.sub("[EMAIL-REDACTED]", s)
        s = _PHONE.sub("[PHONE-REDACTED]", s)
        s = _LONG_ID.sub("[ID-REDACTED]", s)
        return s
    return obj


def assert_no_identifiers(payload: Any) -> list[str]:
    """Return a list of identifier-key paths still present (should be empty).

    Used as a defense-in-depth check before a model call and in tests.
    """
    found: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                klow = str(k).lower().replace("-", "").replace("_", "")
                if klow in {ik.replace("_", "") for ik in _IDENTIFIER_KEYS}:
                    found.append(f"{path}.{k}" if path else str(k))
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(payload, "")
    return found


def redact_structured(obj: Any) -> Any:
    """Deep-redact a structured object for audit/trace persistence (keeps shape)."""
    if isinstance(obj, dict):
        return {k: redact_structured(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_structured(v) for v in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj
