"""CDS Hooks card construction + validation (per the CDS Hooks card schema)."""

from __future__ import annotations

from typing import Any

VALID_INDICATORS = {"info", "warning", "critical"}


def make_card(
    *,
    summary: str,
    detail: str,
    indicator: str = "info",
    source_label: str = "DualBeat CareGuard",
    source_url: str = "",
    evidence_url: str = "",
    override_reasons: list[str] | None = None,
) -> dict[str, Any]:
    if indicator not in VALID_INDICATORS:
        indicator = "info"
    card: dict[str, Any] = {
        "summary": summary[:140],  # CDS Hooks: summary <= 140 chars
        "detail": detail,
        "indicator": indicator,
        "source": {"label": source_label},
    }
    if source_url:
        card["source"]["url"] = source_url
    links = []
    if evidence_url:
        links.append({"label": "Open evidence review", "url": evidence_url, "type": "absolute"})
    if links:
        card["links"] = links
    if override_reasons:
        card["overrideReasons"] = [{"code": f"or-{i}", "display": r} for i, r in enumerate(override_reasons)]
    return card


def validate_card(card: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not card.get("summary"):
        issues.append("card missing summary")
    if len(card.get("summary", "")) > 140:
        issues.append("summary exceeds 140 chars")
    if card.get("indicator") not in VALID_INDICATORS:
        issues.append("invalid indicator")
    if "source" not in card or not card["source"].get("label"):
        issues.append("card missing source.label")
    # A card must never carry an executable order.
    if "suggestions" in card:
        for s in card["suggestions"]:
            for action in s.get("actions", []):
                if action.get("type") == "create" and action.get("autoExecute"):
                    issues.append("card contains an auto-executable order (forbidden)")
    return issues
