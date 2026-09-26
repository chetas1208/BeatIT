"""Parse a drug-label dict into normalized sections + evidence passages.

Works on the CareGuard local-corpus label shape and on openFDA/DailyMed-style
dicts (best-effort). Never invents a section that isn't present.
"""

from __future__ import annotations

from typing import Any

# Canonical section keys → the terms we search under.
SECTION_KEYS = ("contraindications", "boxed_warning", "warnings", "drug_interactions",
                "renal_impairment", "hepatic_impairment", "pregnancy", "geriatric_use",
                "indications", "monitoring")


def sections(label: dict[str, Any]) -> dict[str, str]:
    raw = label.get("sections") or {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(v, str) and v.strip():
            out[k] = v
    return out


def section_text(label: dict[str, Any], *names: str) -> tuple[str, str] | None:
    secs = sections(label)
    for name in names:
        if name in secs:
            return name, secs[name]
    return None


def mentions(label: dict[str, Any], *terms: str) -> tuple[bool, str, str]:
    for name, text in sections(label).items():
        low = text.lower()
        if any(t in low for t in terms):
            return True, name, text
    return False, "", ""


def effective_date(label: dict[str, Any]) -> str | None:
    return label.get("effective_date") or label.get("label_version")


def label_version(label: dict[str, Any]) -> str | None:
    return label.get("label_version") or label.get("effective_date")
