"""Map an RxCUI to therapeutic classes (via RxClass) and list class members.

Membership does not imply interchangeability or equal effectiveness (spec §4).
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.medications import rxclass_client


def classes_for(rxcui: str | None) -> list[dict[str, Any]]:
    return rxclass_client.memberships(rxcui)


def class_members(class_name: str) -> list[dict[str, Any]]:
    return rxclass_client.members_of_class(class_name)


def sibling_members(rxcui: str | None) -> list[dict[str, Any]]:
    """Members of every class this rxcui belongs to, excluding itself."""
    out: list[dict[str, Any]] = []
    seen: set[str] = {rxcui or ""}
    for cls in classes_for(rxcui):
        for m in class_members(cls.get("class_name", "")):
            if m.get("rxcui") not in seen:
                seen.add(m.get("rxcui"))
                m = dict(m)
                m["class_name"] = cls.get("class_name")
                out.append(m)
    return out
