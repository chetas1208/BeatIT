#!/usr/bin/env python3
"""Build the source-derived (silver) reference label set.

Labels come ONLY from deterministic case facts, RxNorm normalization, openFDA
drug-label evidence, documented allergies, and the deterministic organ-system
analysis. No model output, no CareGuard output, no LLM-as-ground-truth.

Outputs (spec §3):
  reference/reference_labels.ndjson
  reference/reference_labels.parquet
  reference/reference_provenance.ndjson
  reference/adjudication_queue.csv      (stratified subset for human review)
  reference/adjudication_template.csv    (blank template for adjudicators)
  reference/label_quality_report.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _bench_common import CASES_DIR, REFERENCE_DIR, RESULTS_DIR  # noqa: E402
from _case_facts import (  # noqa: E402
    compute_allergy_conflicts,
    load_case_facts,
)


def build_reference(facts: dict) -> tuple[dict, list[dict]]:
    """Return (reference_label, provenance_rows) for one case."""
    cid = facts["case_id"]
    prov: list[dict] = []
    assertions: list[dict] = []

    # 1) Expected normalized medications (reconciliation recall target)
    exp_meds = []
    for m in facts["medications"]:
        if not m["resolved"]:
            continue
        exp_meds.append({
            "rxcui": m["rxcui"],
            "normalized_name": m["normalized_name"],
            "ingredients": m["ingredients"],
            "original_text": m["original_text"],
            "fact_id": m["fact_id"],
        })
        assertions.append({
            "assertion_id": f"{cid}:med:{m['rxcui']}",
            "kind": "medication_present",
            "target": m["rxcui"],
            "source": "medication-evidence/normalized-medications.json",
            "source_ref": m["fact_id"],
        })
        prov.append({
            "case_id": cid, "assertion_id": f"{cid}:med:{m['rxcui']}",
            "source_file": "medication-evidence/normalized-medications.json",
            "source_key": "rxcui", "source_value": m["rxcui"],
            "method": m["normalization_method"],
        })

    # 2) Expected allergy conflicts (allergy-vs-active-drug ingredient match)
    exp_allergy = compute_allergy_conflicts(facts)
    for c in exp_allergy:
        aid = f"{cid}:allergy:{c['allergy_fact_id']}"
        assertions.append({
            "assertion_id": aid,
            "kind": "allergy_conflict",
            "target": c["matched_ingredient"],
            "source": "ehr/allergies.csv + normalized-medications.json",
            "source_ref": f"{c['allergy_fact_id']}|{c['medication_fact_id']}",
        })
        prov.append({
            "case_id": cid, "assertion_id": aid,
            "source_file": "ehr/allergies.csv",
            "source_key": "allergy_name", "source_value": c["allergy_name"],
            "method": c["match_basis"],
        })

    # 3) Expected contraindication signals (openFDA label has_contraindications)
    exp_contra = []
    for m in facts["medications"]:
        rx = str(m["rxcui"]) if m["rxcui"] is not None else None
        lab = facts["labels_by_rxcui"].get(rx) if rx else None
        if lab and lab.get("has_contraindications"):
            excerpt = (lab.get("contraindications_excerpt") or "")[:400]
            exp_contra.append({
                "rxcui": rx,
                "normalized_name": m["normalized_name"],
                "label_set_id": lab.get("set_id"),
                "effective_time": lab.get("effective_time"),
                "has_boxed_warning": lab.get("has_boxed_warning", False),
                "contraindications_excerpt": excerpt,
                "fact_id": m["fact_id"],
            })
            aid = f"{cid}:contra:{rx}"
            assertions.append({
                "assertion_id": aid,
                "kind": "contraindication_signal",
                "target": rx,
                "source": "medication-evidence/label-evidence.json",
                "source_ref": lab.get("set_id"),
            })
            prov.append({
                "case_id": cid, "assertion_id": aid,
                "source_file": "medication-evidence/label-evidence.json",
                "source_key": "set_id", "source_value": lab.get("set_id"),
                "method": "openfda_has_contraindications",
            })

    # 4) Expected missing information (deterministic quality warnings)
    exp_missing = list(facts["missingness_warnings"] or [])
    for w in exp_missing:
        aid = f"{cid}:missing:{abs(hash(w)) % 10**8}"
        assertions.append({
            "assertion_id": aid, "kind": "missing_information",
            "target": w, "source": "quality.json",
            "source_ref": "missingness_warnings",
        })

    # 5) Expected organ systems
    exp_organs = sorted(set(facts["organ_systems"]))

    label = {
        "case_id": cid,
        "label_tier": "silver",
        "provenance": {
            "derived_from": [
                "medication-evidence/normalized-medications.json",
                "medication-evidence/label-evidence.json",
                "ehr/allergies.csv", "quality.json",
                "clinical/patient-summary.json",
            ],
            "no_model_used": True,
            "no_system_output_used": True,
        },
        "expected_medications_normalized": exp_meds,
        "expected_allergy_conflicts": exp_allergy,
        "expected_contraindication_signals": exp_contra,
        "expected_missing_information": exp_missing,
        "expected_organ_systems": exp_organs,
        "expected_condition_count": len(facts["conditions"]),
        "assertions": assertions,
        "counts": {
            "medications": len(exp_meds),
            "allergy_conflicts": len(exp_allergy),
            "contraindication_signals": len(exp_contra),
            "missing_information": len(exp_missing),
            "organ_systems": len(exp_organs),
            "assertions": len(assertions),
        },
    }
    return label, prov


def main() -> int:
    import pandas as pd

    # Only index eligible cases; but build reference for ALL that load.
    idx_path = RESULTS_DIR / "case_index.parquet"
    if idx_path.exists():
        idx = pd.read_parquet(idx_path)
        case_ids = idx[idx["status"].isin(
            ["eligible", "eligible_with_warning"])]["case_id"].tolist()
    else:
        case_ids = [d.name for d in sorted(CASES_DIR.iterdir())
                    if d.is_dir() and d.name.startswith("case-")]

    print(f"Building source-derived reference labels for {len(case_ids)} "
          f"cases ...")

    labels: list[dict] = []
    prov_rows: list[dict] = []
    flat_rows: list[dict] = []
    for i, cid in enumerate(case_ids, 1):
        facts = load_case_facts(CASES_DIR / cid)
        label, prov = build_reference(facts)
        labels.append(label)
        prov_rows.extend(prov)
        flat_rows.append({
            "case_id": cid,
            **{f"n_{k}": v for k, v in label["counts"].items()},
        })
        if i % 200 == 0:
            print(f"  ... {i}/{len(case_ids)}")

    # NDJSON
    lbl_path = REFERENCE_DIR / "reference_labels.ndjson"
    with lbl_path.open("w") as f:
        for lbl in labels:
            f.write(json.dumps(lbl) + "\n")
    prov_path = REFERENCE_DIR / "reference_provenance.ndjson"
    with prov_path.open("w") as f:
        for r in prov_rows:
            f.write(json.dumps(r) + "\n")

    # Parquet (flat counts view)
    flat = pd.DataFrame(flat_rows)
    try:
        flat.to_parquet(REFERENCE_DIR / "reference_labels.parquet", index=False)
    except Exception as exc:
        print(f"  (parquet skipped: {exc})")

    # Stratified adjudication queue: sample across allergy/contra presence and
    # medication-count bands so the gold subset is representative.
    flat = flat.merge(
        pd.read_parquet(idx_path)[["case_id", "medication_count",
                                   "organ_system_count"]]
        if idx_path.exists() else flat[["case_id"]],
        on="case_id", how="left",
    )

    def band(n):
        if n is None:
            return "na"
        n = float(n)
        if n <= 10:
            return "few"
        if n <= 40:
            return "many"
        return "poly"

    flat["med_band"] = flat.get("medication_count", 0).map(band)
    flat["has_allergy_conflict"] = flat["n_allergy_conflicts"] > 0
    flat["has_contra"] = flat["n_contraindication_signals"] > 0
    flat["stratum"] = (
        flat["med_band"].astype(str) + "|"
        + flat["has_allergy_conflict"].astype(str) + "|"
        + flat["has_contra"].astype(str)
    )
    # deterministic sample: up to N per stratum, ordered by case_id
    target_total = 120
    strata = sorted(flat["stratum"].unique())
    per = max(1, target_total // max(len(strata), 1))
    picks = []
    for s in strata:
        sub = flat[flat["stratum"] == s].sort_values("case_id")
        picks.extend(sub["case_id"].head(per).tolist())
    picks = picks[:target_total]
    adjud = flat[flat["case_id"].isin(picks)].sort_values("case_id")
    adjud[["case_id", "stratum", "med_band", "n_allergy_conflicts",
           "n_contraindication_signals", "n_medications"]].to_csv(
        REFERENCE_DIR / "adjudication_queue.csv", index=False)

    # Blank template for human adjudicators
    tmpl = adjud[["case_id"]].copy()
    for col in ["allergy_conflicts_correct", "contraindications_correct",
                "medications_correct", "missing_info_correct",
                "adjudicator_id", "notes"]:
        tmpl[col] = ""
    tmpl.to_csv(REFERENCE_DIR / "adjudication_template.csv", index=False)

    # Quality report
    report = {
        "n_cases": len(labels),
        "totals": {
            "medications": int(flat["n_medications"].sum()),
            "allergy_conflicts": int(flat["n_allergy_conflicts"].sum()),
            "contraindication_signals":
                int(flat["n_contraindication_signals"].sum()),
            "missing_information": int(flat["n_missing_information"].sum()),
        },
        "cases_with_allergy_conflict":
            int((flat["n_allergy_conflicts"] > 0).sum()),
        "cases_with_contra_signal":
            int((flat["n_contraindication_signals"] > 0).sum()),
        "adjudication_queue_size": int(len(adjud)),
        "n_strata": int(len(strata)),
        "tier": "silver",
        "note": "source-derived; human-adjudicated gold subset pending",
    }
    (REFERENCE_DIR / "label_quality_report.json").write_text(
        json.dumps(report, indent=2))

    print(f"\nWrote {lbl_path}")
    print(f"Wrote {prov_path}")
    print(f"Wrote adjudication_queue.csv ({len(adjud)} cases, "
          f"{len(strata)} strata)")
    print("\nReference totals:")
    for k, v in report["totals"].items():
        print(f"  {k:26s} {v}")
    print(f"  cases w/ allergy conflict  "
          f"{report['cases_with_allergy_conflict']}")
    print(f"  cases w/ contra signal     "
          f"{report['cases_with_contra_signal']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
