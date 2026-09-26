"""Deterministic builders for the canonical case packet and the evidence packet.

Both are built from case files only — never from a model or from CareGuard
output. The evidence packet is assembled independently of the tested models and
contains NO answer label: only source text (openFDA label excerpts, topic-
matched guideline passages) with full provenance.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS_PATH = REPO_ROOT / "fixtures" / "careguard" / "corpus" / "local_corpus.json"

_STD_DISCLAIMER = (
    "Research and software-testing case assembled from de-identified open "
    "datasets. Not for diagnosis or treatment decisions. Composite modalities "
    "may originate from different de-identified individuals."
)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_vitals(case_dir: Path) -> list[dict[str, Any]]:
    p = case_dir / "ehr" / "vitals.csv"
    if not p.exists():
        return []
    out = []
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("vital")
            if not name:
                continue
            out.append({
                "vital": name,
                "unit": row.get("unit", ""),
                "mean": row.get("mean", ""),
                "min": row.get("min", ""),
                "max": row.get("max", ""),
            })
    return out[:12]


def build_canonical_packet(facts: dict[str, Any], case_dir: Path) -> dict:
    """Canonical, de-duplicated case representation for direct-model arms."""
    cid = facts["case_id"]

    conditions = []
    for c in facts["conditions"][:80]:
        conditions.append({
            "fact_id": c["fact_id"],
            "name": c["text"],
            "status": ("recorded_active"
                       if c.get("clinical_status") == "active"
                       else "recorded_historical"),
            "organ_system": c.get("organ_systems", ""),
        })
    conditions_truncated = len(facts["conditions"]) > 80

    medications = []
    for m in facts["medications"]:
        medications.append({
            "fact_id": m["fact_id"],
            "original_text": m["original_text"],
            "normalized_name": m["normalized_name"],
            "rxcui": m["rxcui"],
            "ingredients": m["ingredients"],
        })

    allergies = [
        {"fact_id": a["fact_id"], "name": a["name"], "type": a["type"]}
        for a in facts["allergies"]
    ]

    labs = []
    for name, v in list(facts["lab_summary"].items())[:30]:
        labs.append({"name": name, "value": v["value"], "unit": v["unit"]})

    demo = facts.get("demographics", {})
    ecg = facts.get("ecg", {})
    ecg_summary = None
    if ecg:
        ecg_summary = {
            "note": "matched external modality (PTB-XL) — different "
                    "de-identified individual; not used for medication safety",
            "interpretation": ecg.get("interpretation")
            or ecg.get("report") or ecg.get("summary"),
        }

    missing = list(facts["missingness_warnings"] or [])
    if conditions_truncated:
        missing.append("condition_list_truncated_for_length")

    return {
        "case_id": cid,
        "data_disclaimer": _STD_DISCLAIMER,
        "demographics": {
            "age": demo.get("age"), "gender": demo.get("gender"),
            "icu_type": demo.get("icu_type"),
        },
        "cardiac_context": list(facts["cardiac_context"]),
        "conditions": conditions,
        "report_condition_mentions": [],
        "medications": medications,
        "proposed_medication": None,
        "allergies": allergies,
        "labs": labs,
        "vitals": _load_vitals(case_dir),
        "procedures": [],
        "missing_information": missing,
        "source_provenance": [{
            "source_dataset": facts["manifest"].get("source_dataset"),
            "provenance_coverage":
                facts["quality"].get("provenance_coverage"),
            "note": "field-level provenance available in provenance.json",
        }],
        "ecg_summary": ecg_summary,
    }


_CORPUS_CACHE: dict | None = None


def _corpus() -> dict:
    global _CORPUS_CACHE
    if _CORPUS_CACHE is None:
        if CORPUS_PATH.exists():
            _CORPUS_CACHE = json.loads(CORPUS_PATH.read_text())
        else:
            _CORPUS_CACHE = {"entries": [], "drug_labels": []}
    return _CORPUS_CACHE


def _match_guidelines(facts: dict) -> list[dict]:
    """Topic-match local-corpus guideline entries to the case, deterministically."""
    corpus = _corpus()
    hay = " ".join(
        [str(x) for x in facts["cardiac_context"]]
        + [c["text"] for c in facts["conditions"]]
        + [m["normalized_name"] or "" for m in facts["medications"]]
    ).casefold()
    out = []
    for e in corpus.get("entries", []):
        topics = [t.casefold() for t in e.get("topics", [])]
        if any(t in hay for t in topics):
            passage = e.get("passage", "")
            out.append({
                "evidence_id": f"guideline:{e.get('source_id')}",
                "source_authority": e.get("organization"),
                "authority_level": e.get("authority_level"),
                "source_title": e.get("title"),
                "source_version": e.get("version"),
                "publication_date": e.get("publication_date"),
                "section": e.get("section"),
                "passage": passage,
                "source_identifier": e.get("canonical_source"),
                "retrieval_timestamp": _now(),
                "hash": _sha(passage),
                "synthetic_excerpt": e.get("synthetic_excerpt", False),
                "recommendation_class": e.get("recommendation_class"),
                "evidence_level": e.get("evidence_level"),
                "applies_to_facts": [
                    m["fact_id"] for m in facts["medications"]
                    if (m["normalized_name"] or "").casefold() in
                    " ".join(e.get("topics", [])).casefold()
                ],
            })
    return out


def build_evidence_packet(facts: dict) -> dict:
    """Authoritative evidence packet — source text only, no answer key."""
    cid = facts["case_id"]

    med_identities = [
        {
            "rxcui": m["rxcui"],
            "normalized_name": m["normalized_name"],
            "ingredients": m["ingredients"],
            "fact_id": m["fact_id"],
        }
        for m in facts["medications"]
    ]

    drug_label_passages = []
    for lab in facts["label_evidence"]:
        rx = lab.get("rxcui")
        for kind, field in (
            ("contraindications", "contraindications_excerpt"),
            ("boxed_warning", "boxed_warning_excerpt"),
        ):
            passage = (lab.get(field) or "").strip()
            if not passage:
                continue
            drug_label_passages.append({
                "evidence_id": f"label:{rx}:{kind}",
                "source_authority": "US FDA (openFDA drug/label)",
                "source_title": f"Structured Product Label ({kind})",
                "source_version": lab.get("effective_time"),
                "publication_date": lab.get("effective_time"),
                "section": kind,
                "passage": passage[:800],
                "source_identifier": lab.get("set_id"),
                "label_id": lab.get("label_id"),
                "retrieval_timestamp": _now(),
                "hash": _sha(passage),
                "applies_to_rxcui": rx,
                "note": "verbatim source label text; not an answer label",
            })

    guideline_passages = _match_guidelines(facts)

    retrieval_failures = []
    if not drug_label_passages:
        retrieval_failures.append("no_openfda_label_evidence_for_case")
    if not guideline_passages:
        retrieval_failures.append("no_topic_matched_guideline_passages")

    source_versions = {
        "openfda_labels": sorted({
            lab.get("effective_time")
            for lab in facts["label_evidence"] if lab.get("effective_time")
        }),
        "guideline_corpus_version": _corpus().get("corpus_version"),
    }

    freshness = []
    for e in guideline_passages:
        if e.get("synthetic_excerpt"):
            freshness.append(
                f"{e['evidence_id']}: synthetic excerpt of a real guideline "
                "(software-testing corpus)"
            )

    return {
        "case_id": cid,
        "medication_identities": med_identities,
        "guideline_passages": guideline_passages,
        "drug_label_passages": drug_label_passages,
        "interaction_records": [],
        "source_versions": source_versions,
        "retrieval_failures": retrieval_failures,
        "source_freshness_warnings": freshness,
        "packet_note": (
            "Assembled independently of the tested models and of CareGuard. "
            "Contains source text only; no reference label or grading key is "
            "included."
        ),
    }
