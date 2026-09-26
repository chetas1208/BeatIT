#!/usr/bin/env python
"""verify:medication-sources — validate the medication evidence federation.

Checks each source is configured/versioned as expected, DrugBank refuses without
a license, no Kaggle set is registered as authority, and local snapshots carry a
hash. Exit non-zero on hard failure.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def main() -> int:
    from python.hearttwin.careguard.evidence import local_corpus
    from python.hearttwin.careguard.medications import source_registry

    statuses = {s["source_id"]: s for s in source_registry.all_source_status()}
    for sid in ("rxnorm", "rxclass", "dailymed", "openfda", "orange_book", "ddinter", "sider", "drugcentral", "drugbank"):
        check(f"source registered: {sid}", sid in statuses)

    check("DailyMed is tier A", statuses["dailymed"]["authority_tier"] == "A")
    check("DDInter is tier B (supplemental)", statuses["ddinter"]["authority_tier"] == "B")
    check("DrugBank tier C not loadable w/o license", statuses["drugbank"].get("loadable") is False)

    # Local snapshots carry hashes.
    labels = local_corpus.drug_labels()
    check("drug-label snapshots present", len(labels) > 0)
    check("every local label has a source_hash", all(l.get("sha256") for l in labels))
    guides = local_corpus.guideline_entries()
    check("every local guideline has a source_hash", all(g.get("sha256") for g in guides))

    # No Kaggle registered as authority.
    try:
        source_registry.assert_not_prohibited("kaggle")
        check("no Kaggle data as clinical authority", False)
    except Exception:
        check("no Kaggle data as clinical authority", True)

    # Supplemental corpus is clearly marked non-authoritative.
    med = local_corpus.med_sources()
    check("supplemental corpus carries a NON-AUTHORITATIVE notice",
          "NON-AUTHORITATIVE" in (med.get("notice", "").upper()))

    print()
    if FAIL:
        print(f"VERIFY:MEDICATION-SOURCES FAILED — {len(FAIL)}: {', '.join(FAIL)}")
        return 1
    print("VERIFY:MEDICATION-SOURCES PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
