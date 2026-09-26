#!/usr/bin/env python3
"""Stage 11 — cohort analysis, charts, and HTML quality report (spec §14).

Consumes the cohort/ tables (stage 10) and per-case FHIR meta (stage 08).
Produces analysis/*.csv, analysis/cohort_summary.{json,md}, the charts in
analysis/charts/, and analysis/cohort_quality_report.html.
"""
from __future__ import annotations

import base64
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import classify as X  # noqa: E402

FHIR_OUT = C.STAGING / "fhir"


def _b64(path):
    return base64.b64encode(path.read_bytes()).decode()


def savefig(fig, name):
    p = C.CHARTS / name
    fig.savefig(p, dpi=100, bbox_inches="tight")
    return p


def main() -> None:
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    C.ensure_dirs()
    log = C.get_logger("11_run_analysis")
    cfg = C.load_config()
    log.info("=== Stage 11: cohort analysis ===")

    mani = pd.read_csv(C.COHORT / "cohort_manifest.csv")
    feats = pd.read_csv(C.COHORT / "patient_features.csv")
    dxt = pd.read_csv(C.COHORT / "diagnoses.csv")
    medt = pd.read_csv(C.COHORT / "medications.csv")
    labt = pd.read_csv(C.COHORT / "labs.csv")
    ecg = pd.read_csv(C.COHORT / "ecg_assignments.csv")
    n = len(mani)

    # ---- composition ----
    comp = {
        "total_packaged_cases": n,
        "real_eicu_cases": int((mani.source_type == "real").sum()),
        "synthetic_fallback_cases": int((mani.source_type != "real").sum()),
        "cases_by_tier": mani.selection_tier.value_counts().to_dict(),
        "cases_with_ecg": int(mani.ecg_assigned.sum()),
        "cases_without_ecg": int((~mani.ecg_assigned.astype(bool)).sum()),
        "cases_with_echo": int(mani.echo_assigned.sum()) if "echo_assigned" in mani else 0,
        "echo_ef_category_distribution": (mani.echo_ef_category.value_counts().to_dict()
                                          if "echo_ef_category" in mani else {}),
        "sex_distribution": mani.gender.value_counts().to_dict(),
        "age_band_distribution": mani.age_band.value_counts().to_dict(),
        "icu_type_distribution": mani.icu_type.value_counts().to_dict(),
    }

    # ---- cardiovascular ----
    cv_counts = {}
    for cat in X.CV_CATEGORIES:
        col = f"cv_{cat}"
        cv_counts[cat] = int(feats[col].sum()) if col in feats else 0
    cardio = {
        "heart_failure": cv_counts["heart_failure"],
        "arrhythmia": cv_counts["atrial_fibrillation"] + cv_counts["other_arrhythmia"],
        "mi_acs": cv_counts["myocardial_infarction_acs"],
        "hypertension": cv_counts["hypertension"], "cardiac_arrest": cv_counts["cardiac_arrest"],
        "cardiomyopathy": cv_counts["cardiomyopathy"], "cardiac_surgery": cv_counts["cardiac_surgery"],
        "by_category": cv_counts,
    }

    # ---- multimorbidity ----
    norg = mani.n_noncardiac_organs.tolist()
    organ_cols = [f"organ_{o}" for o in X.ORGAN_SYSTEMS if f"organ_{o}" in feats]
    cooc = {}
    for o in X.ORGAN_SYSTEMS:
        col = f"organ_{o}"
        if col in feats:
            cooc[f"cardiovascular+{o}"] = int(feats[col].sum())
    multimorb = {
        "mean_noncardiac_organ_systems": round(st.mean(norg), 3),
        "median_noncardiac_organ_systems": st.median(norg),
        "cardiovascular_plus": cooc,
        "three_or_more_organ_systems": int((mani.n_noncardiac_organs >= 2).sum()),
    }

    # organ co-occurrence matrix
    M = np.zeros((len(organ_cols), len(organ_cols)), dtype=int)
    fv = feats[organ_cols].values
    for i in range(len(organ_cols)):
        for j in range(len(organ_cols)):
            M[i, j] = int(((fv[:, i] == 1) & (fv[:, j] == 1)).sum())
    labels = [c.replace("organ_", "") for c in organ_cols]
    pd.DataFrame(M, index=labels, columns=labels).to_csv(C.ANALYSIS / "organ_comorbidity_matrix.csv")

    # ---- medications ----
    med_per_case = mani.n_medications.tolist()
    top_meds = medt[medt.normalized_name.notna()].normalized_name.value_counts().head(30)
    resolved = int(medt.resolved.sum())
    total_med_rows = len(medt)
    mn_report = pd.read_csv(C.ANALYSIS / "medication_normalization_report.csv")
    # therapeutic duplication: same normalized ingredient >1 within a case
    dup_cases = 0
    for cid, g in medt.groupby("case_id"):
        names = g.normalized_name.dropna()
        if names.duplicated().any():
            dup_cases += 1
    meds_an = {
        "mean_medications_per_case": round(st.mean(med_per_case), 2),
        "median_medications_per_case": st.median(med_per_case),
        "unique_normalized_strings": int(mn_report.shape[0]),
        "normalization_rate": round(int(mn_report.resolved.sum()) / max(len(mn_report), 1), 4),
        "unresolved_strings": int((~mn_report.resolved).sum()),
        "cases_with_allergy_data": int((mani.n_allergies > 0).sum()),
        "label_evidence_unique": int(mn_report.has_label.sum()),
        "cases_with_possible_therapeutic_duplication": dup_cases,
    }
    top_meds.rename_axis("normalized_name").reset_index(name="n_cases").to_csv(
        C.ANALYSIS / "medication_distribution.csv", index=False)

    # ---- labs ----
    def lab_avail(name):
        col = f"lab_{name.replace(' ', '_')}"
        return int(feats[col].sum()) if col in feats else 0
    labs_an = {name: lab_avail(name) for name in
               ["Creatinine", "Potassium", "Sodium", "AST", "ALT", "INR", "Troponin I",
                "Troponin T", "BNP", "Lactate"]}
    # missingness overall + by morbidity group
    miss_rows = []
    all_lab_names = sorted(labt.canonical.unique()) if len(labt) else []
    per_case_labs = labt.groupby("case_id").canonical.apply(set).to_dict()
    for lname in all_lab_names:
        have = sum(1 for s in per_case_labs.values() if lname in s)
        miss_rows.append({"lab": lname, "cases_with": have, "cases_missing": n - have,
                          "missing_fraction": round((n - have) / n, 4)})
    pd.DataFrame(miss_rows).to_csv(C.ANALYSIS / "laboratory_missingness.csv", index=False)

    # ---- ECG ----
    assigned = ecg[ecg.assigned == True]  # noqa: E712
    def feat_cov(feat):
        return int(assigned.match_features.fillna("").str.contains(feat).sum())
    ecg_an = {
        "selected_records": int(assigned.shape[0]),
        "superclass_distribution": assigned.ecg_primary_superclass.value_counts().to_dict(),
        "matched_on_broad_cardiac_category": feat_cov("broad_cardiac_category"),
        "matched_on_sex": feat_cov("sex"), "matched_on_age_band": feat_cov("age_band"),
        "rhythm_label_counts": assigned.ecg_rhythm.fillna("none").value_counts().head(15).to_dict(),
        "matching_limitations": "ECG matched on broad features only; different deidentified individual than the EHR.",
    }
    assigned.ecg_primary_superclass.value_counts().rename_axis("superclass").reset_index(
        name="n_cases").to_csv(C.ANALYSIS / "ECG_label_distribution.csv", index=False)

    # ---- FHIR ----
    metas = [C.read_json(FHIR_OUT / f"{cid}.meta.json") for cid in mani.case_id
             if (FHIR_OUT / f"{cid}.meta.json").exists()]
    rt_total = {}
    unmapped_conditions = 0
    total_conditions = 0
    ref_fail = 0
    for m in metas:
        for rt, c in m.get("resource_counts", {}).items():
            rt_total[rt] = rt_total.get(rt, 0) + c
        ref_fail += sum(1 for iss in m.get("issues", []) if "unresolved reference" in iss)
    # unmapped codes: conditions in bundles with empty coding
    med_coded = medt.rxcui.notna().sum()
    fhir_an = {
        "valid_bundle_rate": round(int(mani.fhir_valid.sum()) / n, 4),
        "resource_counts_total": rt_total,
        "reference_resolution_failures": int(ref_fail),
        "medication_rxnorm_coverage": round(int(med_coded) / max(total_med_rows, 1), 4),
        "mean_resources_per_bundle": round(st.mean(_rv), 2) if (_rv := mani.fhir_resources.dropna().tolist()) else 0,
    }

    # source coverage
    pd.DataFrame([
        {"source": "eICU-CRD Demo 2.0.1", "modality": "structured EHR", "cases": n,
         "real": True, "license": cfg["sources"]["eicu"]["license"]},
        {"source": "PTB-XL 1.0.1", "modality": "12-lead ECG", "cases": int(mani.ecg_assigned.sum()),
         "real": True, "license": cfg["sources"]["ptbxl"]["license"]},
    ]).to_csv(C.ANALYSIS / "source_coverage.csv", index=False)
    pd.DataFrame([{"cv_category": k, "n_cases": v} for k, v in cv_counts.items()]).to_csv(
        C.ANALYSIS / "heart_condition_distribution.csv", index=False)

    summary = {"generated_at": C.now_iso(), "composition": comp, "cardiovascular": cardio,
               "multimorbidity": multimorb, "medications": meds_an, "laboratory": labs_an,
               "ecg": ecg_an, "fhir": fhir_an}
    C.write_json(C.ANALYSIS / "cohort_summary.json", summary)

    # ---- charts ----
    plt.rcParams.update({"figure.autolayout": True, "font.size": 9})
    fig, ax = plt.subplots(figsize=(7, 3.5))
    order = ["18-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80-89", "90+", "unknown"]
    counts = [comp["age_band_distribution"].get(b, 0) for b in order]
    ax.bar(order, counts, color="#7c3aed"); ax.set_title("Age-band distribution"); ax.tick_params(axis="x", rotation=45)
    savefig(fig, "age_distribution.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(M, cmap="magma")
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=90)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
    ax.set_title("Organ co-occurrence (cases)"); fig.colorbar(im, fraction=0.046)
    savefig(fig, "organ_comorbidity_heatmap.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    items = sorted(cv_counts.items(), key=lambda x: -x[1])
    ax.barh([k for k, _ in items], [v for _, v in items], color="#dc2626")
    ax.invert_yaxis(); ax.set_title("Cardiovascular category distribution")
    savefig(fig, "cardiac_condition_distribution.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.hist(med_per_case, bins=30, color="#2563eb"); ax.set_title("Medications per case")
    ax.set_xlabel("n medications"); ax.set_ylabel("cases")
    savefig(fig, "medication_count_distribution.png"); plt.close(fig)

    md = pd.DataFrame(miss_rows).sort_values("missing_fraction")
    fig, ax = plt.subplots(figsize=(7, max(4, len(md) * 0.22)))
    ax.barh(md.lab, 1 - md.missing_fraction, color="#059669")
    ax.set_title("Lab availability (fraction of cases)"); ax.set_xlim(0, 1)
    savefig(fig, "lab_missingness.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.5))
    sc = assigned.ecg_primary_superclass.value_counts()
    ax.bar(sc.index, sc.values, color="#0891b2"); ax.set_title("ECG superclass distribution")
    savefig(fig, "ECG_superclass_distribution.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.5))
    rc = sorted(rt_total.items(), key=lambda x: -x[1])
    ax.barh([k for k, _ in rc], [v for _, v in rc], color="#ea580c"); ax.invert_yaxis()
    ax.set_title("FHIR resource counts (total)")
    savefig(fig, "FHIR_resource_counts.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.hist(mani.overall_completeness_score.dropna(), bins=25, color="#16a34a")
    ax.set_title("Completeness score distribution"); ax.set_xlabel("overall completeness")
    savefig(fig, "completeness_score_distribution.png"); plt.close(fig)

    # ---- markdown + HTML ----
    write_markdown(summary)
    write_html(summary, cfg)
    log.info("=== Stage 11 complete: analysis + 8 charts + HTML report ===")
    print("analysis_done=1")


def write_markdown(s):
    c = s["composition"]
    lines = [
        "# HeartTwin CareGuard — Cohort Summary", "",
        f"_Generated {s['generated_at']}_", "",
        f"- Total packaged cases: **{c['total_packaged_cases']}**",
        f"- Real eICU cases: **{c['real_eicu_cases']}**  |  Synthetic fallback: **{c['synthetic_fallback_cases']}**",
        f"- Cases with external ECG: **{c['cases_with_ecg']}**  |  without: **{c['cases_without_ecg']}**",
        f"- Tiers: {c['cases_by_tier']}",
        f"- Sex: {c['sex_distribution']}",
        "", "## Cardiovascular", f"- {s['cardiovascular']}",
        "", "## Multimorbidity",
        f"- Mean non-cardiac organ systems: {s['multimorbidity']['mean_noncardiac_organ_systems']}",
        f"- Median: {s['multimorbidity']['median_noncardiac_organ_systems']}",
        f"- Cardiovascular co-occurrence: {s['multimorbidity']['cardiovascular_plus']}",
        "", "## Medications", f"- {s['medications']}",
        "", "## Laboratory availability", f"- {s['laboratory']}",
        "", "## ECG (external matched modality)", f"- {s['ecg']}",
        "", "## FHIR", f"- {s['fhir']}",
        "", "> Composite modalities may originate from different deidentified individuals. "
        "Research/software-testing dataset only.",
    ]
    (C.ANALYSIS / "cohort_summary.md").write_text("\n".join(lines))


def write_html(s, cfg):
    charts = ["age_distribution.png", "cardiac_condition_distribution.png",
              "organ_comorbidity_heatmap.png", "medication_count_distribution.png",
              "lab_missingness.png", "ECG_superclass_distribution.png",
              "FHIR_resource_counts.png", "completeness_score_distribution.png"]
    imgs = "".join(
        f'<figure><img src="data:image/png;base64,{_b64(C.CHARTS / ch)}"/>'
        f'<figcaption>{ch}</figcaption></figure>'
        for ch in charts if (C.CHARTS / ch).exists())
    c = s["composition"]
    import json as _j
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>CareGuard Cohort Quality Report</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,sans-serif;margin:2rem;max-width:1100px;color:#1a1a1a}}
h1{{color:#7c3aed}} .warn{{background:#fef3c7;border-left:4px solid #f59e0b;padding:.75rem 1rem;border-radius:6px}}
figure{{display:inline-block;margin:.5rem;vertical-align:top}} img{{max-width:520px;border:1px solid #e5e7eb;border-radius:8px}}
figcaption{{font-size:.8rem;color:#666;text-align:center}} pre{{background:#f6f6f8;padding:1rem;border-radius:8px;overflow:auto;font-size:.8rem}}
table{{border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:4px 10px;font-size:.85rem}}
</style></head><body>
<h1>HeartTwin CareGuard — Cohort Quality Report</h1>
<p class="warn"><b>Research and software-testing dataset. Not for diagnosis or treatment decisions.</b><br>
Composite modalities may originate from different deidentified individuals. The ECG is a matched external
modality from PTB-XL and does not originate from the same individual as the eICU record.</p>
<p>Generated {s['generated_at']}</p>
<table>
<tr><th>Total cases</th><td>{c['total_packaged_cases']}</td>
<th>Real eICU</th><td>{c['real_eicu_cases']}</td>
<th>Synthetic</th><td>{c['synthetic_fallback_cases']}</td></tr>
<tr><th>With ECG</th><td>{c['cases_with_ecg']}</td>
<th>FHIR valid rate</th><td>{s['fhir']['valid_bundle_rate']}</td>
<th>Norm. rate</th><td>{s['medications']['normalization_rate']}</td></tr>
</table>
<h2>Charts</h2>{imgs}
<h2>Full summary</h2><pre>{_j.dumps(s, indent=2, default=str)}</pre>
</body></html>"""
    (C.ANALYSIS / "cohort_quality_report.html").write_text(html)


if __name__ == "__main__":
    main()
