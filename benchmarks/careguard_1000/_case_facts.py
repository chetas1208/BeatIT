"""Deterministic loader for a single case's facts.

Both the reference-label builder and the packet builders read from here, so the
canonical case representation, deduplication, and normalization are defined in
exactly one place. Nothing here calls a model. Every value traces to a file in
the case directory.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


def _norm_name(s: str | None) -> str:
    if not s:
        return ""
    s = s.casefold().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, ValueError):
        return default


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


# A small, curated brand/synonym -> active-ingredient map for deterministic
# allergy-to-medication matching. Deliberately conservative: it is a
# reference-construction dictionary (not a model), used only to link a
# documented allergy to a documented medication ingredient. Extend as needed;
# every entry is a well-known US brand->ingredient mapping.
BRAND_TO_INGREDIENT: dict[str, list[str]] = {
    "fosamax": ["alendronate"],
    "levaquin": ["levofloxacin"],
    "bactrim": ["sulfamethoxazole", "trimethoprim"],
    "septra": ["sulfamethoxazole", "trimethoprim"],
    "lasix": ["furosemide"],
    "coumadin": ["warfarin"],
    "zocor": ["simvastatin"],
    "lipitor": ["atorvastatin"],
    "glucophage": ["metformin"],
    "zithromax": ["azithromycin"],
    "augmentin": ["amoxicillin", "clavulanate"],
    "amoxil": ["amoxicillin"],
    "keflex": ["cephalexin"],
    "ancef": ["cefazolin"],
    "rocephin": ["ceftriaxone"],
    "cipro": ["ciprofloxacin"],
    "flagyl": ["metronidazole"],
    "zosyn": ["piperacillin", "tazobactam"],
    "vancocin": ["vancomycin"],
    "motrin": ["ibuprofen"],
    "advil": ["ibuprofen"],
    "aleve": ["naproxen"],
    "toradol": ["ketorolac"],
    "percocet": ["oxycodone", "acetaminophen"],
    "vicodin": ["hydrocodone", "acetaminophen"],
    "dilantin": ["phenytoin"],
    "tegretol": ["carbamazepine"],
    "neurontin": ["gabapentin"],
    "lopressor": ["metoprolol"],
    "toprol": ["metoprolol"],
    "norvasc": ["amlodipine"],
    "lisinopril": ["lisinopril"],
    "protonix": ["pantoprazole"],
    "prilosec": ["omeprazole"],
    "plavix": ["clopidogrel"],
    "aspirin": ["aspirin"],
    "asa": ["aspirin"],
    "nsaid": ["ibuprofen", "naproxen", "ketorolac", "aspirin"],
    "penicillin": ["penicillin", "amoxicillin", "ampicillin"],
    "sulfa": ["sulfamethoxazole", "sulfasalazine"],
    "codeine": ["codeine"],
    "morphine": ["morphine"],
    "heparin": ["heparin"],
    "insulin": ["insulin"],
    "statin": ["atorvastatin", "simvastatin", "rosuvastatin", "pravastatin"],
    "iodine": ["iodine"],
    "contrast": ["iohexol", "iodine"],
    "calcionate": ["calcium"],
}


def allergy_ingredient_candidates(allergy_name: str) -> set[str]:
    """Deterministically expand an allergy name to candidate ingredients."""
    n = _norm_name(allergy_name)
    out: set[str] = set()
    if not n:
        return out
    # direct: the allergy name itself may be an ingredient
    out.add(n)
    # token-level brand lookups
    for tok in n.split():
        if tok in BRAND_TO_INGREDIENT:
            out.update(BRAND_TO_INGREDIENT[tok])
    if n in BRAND_TO_INGREDIENT:
        out.update(BRAND_TO_INGREDIENT[n])
    return {_norm_name(x) for x in out if x}


def load_case_facts(case_dir: Path) -> dict[str, Any]:
    """Load a deterministic, deduplicated view of one case."""
    cid = case_dir.name
    manifest = _load_json(case_dir / "manifest.json", {}) or {}
    quality = _load_json(case_dir / "quality.json", {}) or {}
    summary = _load_json(case_dir / "clinical" / "patient-summary.json", {}) or {}
    normalized = _load_json(
        case_dir / "medication-evidence" / "normalized-medications.json", []
    ) or []
    label_ev = _load_json(
        case_dir / "medication-evidence" / "label-evidence.json", []
    ) or []
    ecg = _load_json(case_dir / "ecg" / "ecg.json", {}) or {}

    diagnoses = _read_csv(case_dir / "ehr" / "diagnoses.csv")
    allergies = _read_csv(case_dir / "ehr" / "allergies.csv")
    meds_raw = _read_csv(case_dir / "ehr" / "medications.csv")
    labs = _read_csv(case_dir / "ehr" / "labs.csv")

    # --- Conditions (dedup by normalized text) ---
    conditions = []
    seen_cond = set()
    for i, d in enumerate(diagnoses):
        text = d.get("text", "").strip()
        key = _norm_name(text)
        if not key or key in seen_cond:
            continue
        seen_cond.add(key)
        conditions.append({
            "fact_id": f"cond-{d.get('source_row_id', i)}",
            "text": text,
            "icd_code": d.get("icd_code", ""),
            "clinical_status": d.get("clinical_status", ""),
            "active_upon_discharge": d.get("active_upon_discharge", ""),
            "organ_systems": d.get("organ_systems", ""),
            "cv_categories": d.get("cv_categories", ""),
        })

    # --- Medications: dedup by rxcui/normalized_name from RxNorm file ---
    meds = []
    seen_med = set()
    for i, m in enumerate(normalized):
        rxcui = m.get("rxcui")
        nn = m.get("normalized_name")
        key = rxcui or _norm_name(nn) or _norm_name(m.get("original_text"))
        if not key or key in seen_med:
            continue
        seen_med.add(key)
        ingredients = [
            _norm_name(ing.get("name"))
            for ing in (m.get("ingredients") or [])
            if ing.get("name")
        ]
        meds.append({
            "fact_id": f"med-{rxcui or i}",
            "original_text": m.get("original_text"),
            "normalized_name": nn,
            "rxcui": rxcui,
            "ingredients": ingredients,
            "confidence": m.get("confidence"),
            "resolved": not m.get("unresolved", False) and rxcui is not None,
            "normalization_method": m.get("normalization_method"),
        })

    # Set of all active ingredient tokens for allergy matching
    ingredient_index: dict[str, str] = {}  # ingredient -> med fact_id
    for m in meds:
        for ing in m["ingredients"]:
            ingredient_index.setdefault(ing, m["fact_id"])
        nn = _norm_name(m["normalized_name"])
        if nn:
            ingredient_index.setdefault(nn, m["fact_id"])

    # --- Allergies (dedup) ---
    allergy_list = []
    seen_alg = set()
    for i, a in enumerate(allergies):
        name = a.get("name", "").strip()
        key = _norm_name(name)
        if not key or key in seen_alg:
            continue
        seen_alg.add(key)
        allergy_list.append({
            "fact_id": f"alg-{a.get('source_row_id', i)}",
            "name": name,
            "type": a.get("type", ""),
        })

    # --- openFDA label evidence, keyed by rxcui ---
    labels_by_rxcui = {}
    for lab in label_ev:
        rx = lab.get("rxcui")
        if rx:
            labels_by_rxcui[str(rx)] = lab

    # --- Lab summary (dedup by canonical name, keep last value) ---
    lab_summary = {}
    for row in labs:
        canon = row.get("canonical") or row.get("labname")
        if canon:
            lab_summary[canon] = {
                "value": row.get("value") or row.get("text"),
                "unit": row.get("unit", ""),
                "loinc": row.get("loinc", ""),
            }

    return {
        "case_id": cid,
        "manifest": manifest,
        "quality": quality,
        "summary": summary,
        "demographics": summary.get("demographics", {}),
        "cardiac_context": summary.get("cardiovascular_context", []),
        "organ_systems": (
            list(summary.get("cardiovascular_context", []))
            + list(summary.get("noncardiac_organ_systems", []))
        ),
        "noncardiac_organ_systems": summary.get("noncardiac_organ_systems", []),
        "conditions": conditions,
        "medications": meds,
        "ingredient_index": ingredient_index,
        "allergies": allergy_list,
        "labels_by_rxcui": labels_by_rxcui,
        "label_evidence": label_ev,
        "lab_summary": lab_summary,
        "missingness_warnings": quality.get("missingness_warnings", []),
        "completeness_score": quality.get("overall_completeness_score"),
        "ecg": ecg,
        "disclaimers": manifest.get("disclaimers", []),
    }


def compute_allergy_conflicts(facts: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic allergy-vs-active-medication ingredient matches."""
    conflicts = []
    ing_index = facts["ingredient_index"]
    for alg in facts["allergies"]:
        cands = allergy_ingredient_candidates(alg["name"])
        for cand in cands:
            if cand in ing_index:
                conflicts.append({
                    "allergy_fact_id": alg["fact_id"],
                    "allergy_name": alg["name"],
                    "matched_ingredient": cand,
                    "medication_fact_id": ing_index[cand],
                    "match_basis": "rxnorm_ingredient_or_brand_map",
                })
                break  # one conflict per allergy is enough for recall
    return conflicts
