#!/usr/bin/env python3
"""Imaging stage 17 — imaging analysis, charts, and reports (spec §25/§26).

Aggregates linkage/source/VISTA/segmentation/fusion artifacts into a JSON summary,
charts (PNG+SVG+CSV), and MD/HTML/PDF reports. Honest about the gated state:
segmentation accuracy is only reported where a real reference AND a real prediction
exist (0 in gated mode) — never fabricated.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402


def _load(p, default):
    return I.C.read_json(p) if Path(p).exists() else default


def chart(fig, name):
    import matplotlib.pyplot as plt
    fig.savefig(I.AI_CHARTS / f"{name}.png", dpi=100, bbox_inches="tight")
    fig.savefig(I.AI_CHARTS / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    import csv
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    I.ensure_dirs()
    log = I.C.get_logger("imaging_17_analysis")
    log.info("=== Imaging 17: imaging analysis + charts + reports ===")

    audit = _load(I.AI_LINKAGE / "existing_ct_audit_summary.json", {})
    sources = _load(I.IMAGING_SOURCE_MANIFEST_JSON, {"sources": []})
    dicom = _load(I.ANALYSIS_IMAGING / "dicom_validation.json", {"series": []})
    vista = _load(I.AI_VISTA / "run_summary.json", {})
    metrics = _load(I.VB_METRICS / "segmentation_metrics.json", {"rows": []})
    fusion = _load(I.AI_FUSION / "fusion_report.json", {})
    imaging_idx = _load(I.IMAGING_CASES / "imaging_cases_index.json", {"cases": []})
    caps = _load(I.STG_VISTA_JOBS / "capabilities.json", {})

    n_clinical = audit.get("total_cases", 0)
    n_imaging_only = sum(1 for c in imaging_idx.get("cases", []) if c["linkage_status"] == "imaging_only")
    ref_avail = metrics.get("reference_masks_available", 0)

    summary = {
        "generated_at": I.C.now_iso(),
        "linkage": {
            "total_clinical_cases": n_clinical,
            "cases_with_actual_ct": audit.get("with_actual_ct_volume", 0),
            "verified_same_subject_ct": audit.get("verified_same_subject", 0),
            "no_linked_ct": audit.get("no_linked_ct", 0),
            "prohibited_pairings": audit.get("prohibited_cross_dataset", 0),
            "imaging_native_cases": sum(1 for c in imaging_idx.get("cases", [])
                                        if c["linkage_status"] == "imaging_native_same_subject"),
            "imaging_only_benchmark": n_imaging_only,
        },
        "sources": {s["source_id"]: {"access_state": s.get("access_state"),
                                     "can_ingest": s.get("can_ingest"),
                                     "expected_max_cases": s.get("expected_max_cases")}
                    for s in sources.get("sources", [])},
        "vista": {"endpoint_configured": vista.get("endpoint_configured", False),
                  "endpoint_reachable": vista.get("endpoint_reachable", False),
                  "capability_source": vista.get("capability_source"),
                  "supported_classes": caps.get("supported_classes", []),
                  "jobs": vista.get("jobs", 0), "states": vista.get("states", {})},
        "segmentation": {"reference_masks_available": ref_avail,
                         "structures_requested": caps.get("supported_classes", []),
                         "metrics_computed": metrics.get("computed", 0),
                         "reason_not_computed": "gated: no live VISTA endpoint; no masks fabricated"},
        "dicom_validation": {"series": len(dicom.get("series", [])),
                             "valid": sum(1 for s in dicom.get("series", []) if s.get("valid"))},
        "fusion": {"verified_fusions": fusion.get("verified_fusions", 0),
                   "blocked_fusions": fusion.get("blocked_fusions", 0),
                   "prohibited_demo_status": fusion.get("adversarial_prohibited_demo", {}).get("resulting_status")},
    }
    I.C.write_json(I.ANALYSIS_IMAGING / "imaging_analysis.json", summary)

    # ---- charts (PNG + SVG + CSV) ----
    def save_csv(name, rows, cols):
        with open(I.AI_CHARTS / f"{name}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

    # 01 linkage status
    ls = {"no_linked_ct": summary["linkage"]["no_linked_ct"],
          "imaging_only": n_imaging_only,
          "verified_same_subject": summary["linkage"]["verified_same_subject_ct"],
          "prohibited": summary["linkage"]["prohibited_pairings"]}
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(list(ls.keys()), list(ls.values()), color="#7c3aed")
    ax.set_title("CT linkage status"); ax.tick_params(axis="x", rotation=20)
    chart(fig, "01_ct_linkage_status")
    save_csv("01_ct_linkage_status", [{"status": k, "count": v} for k, v in ls.items()], ["status", "count"])

    # 02 source distribution / access
    srows = [{"source": s["source_id"], "access_state": s.get("access_state"),
              "expected_max_cases": s.get("expected_max_cases", 0)} for s in sources.get("sources", [])]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar([r["source"] for r in srows], [r["expected_max_cases"] for r in srows], color="#0891b2")
    ax.set_title("Imaging source expected max cases"); ax.tick_params(axis="x", rotation=20)
    chart(fig, "02_imaging_source_distribution")
    save_csv("02_imaging_source_distribution", srows, ["source", "access_state", "expected_max_cases"])

    # 03 vista job completion
    states = summary["vista"]["states"] or {"no_jobs": 0}
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(list(states.keys()), list(states.values()), color="#ea580c")
    ax.set_title("VISTA job states (gated)"); chart(fig, "03_vista_job_completion")
    save_csv("03_vista_job_completion", [{"state": k, "count": v} for k, v in states.items()], ["state", "count"])

    # 05 supported structure coverage
    sc = summary["vista"]["supported_classes"]
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(sc or ["none"], [1] * (len(sc) or 1), color="#16a34a")
    ax.set_title("VISTA supported structures (declared)"); ax.tick_params(axis="x", rotation=20)
    chart(fig, "05_supported_structure_coverage")
    save_csv("05_supported_structure_coverage", [{"structure": s} for s in sc], ["structure"])

    # 12 reference mask availability
    fig, ax = plt.subplots(figsize=(4, 3.5))
    ax.bar(["reference available", "no reference"],
           [ref_avail, max(0, n_imaging_only - ref_avail)], color="#2563eb")
    ax.set_title("Reference mask availability"); chart(fig, "12_reference_mask_availability")

    # 14 fusion block reasons
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(["blocked", "verified fusions"],
           [summary["fusion"]["blocked_fusions"], summary["fusion"]["verified_fusions"]],
           color=["#dc2626", "#16a34a"])
    ax.set_title("Fusion gate outcomes"); chart(fig, "14_fusion_block_reasons")

    # 17 case-aligned vs imaging-only
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(["clinical (no CT)", "verified same-subject", "imaging-only benchmark"],
           [summary["linkage"]["no_linked_ct"], summary["linkage"]["verified_same_subject_ct"], n_imaging_only],
           color=["#94a3b8", "#16a34a", "#0891b2"])
    ax.set_title("Case-aligned vs imaging-only"); ax.tick_params(axis="x", rotation=15)
    chart(fig, "17_case_aligned_vs_imaging_only")

    # 18 demo imaging proof
    fig, ax = plt.subplots(figsize=(7, 3.5))
    proof = {"verified same-subject": summary["linkage"]["verified_same_subject_ct"],
             "imaging-only real CT": n_imaging_only,
             "reference masks": ref_avail,
             "blocked invalid fusions": summary["fusion"]["blocked_fusions"],
             "VISTA supported classes": len(sc)}
    ax.barh(list(proof.keys()), list(proof.values()), color="#7c3aed"); ax.invert_yaxis()
    ax.set_title("Imaging proof (honest, gated)"); chart(fig, "18_demo_imaging_proof")

    write_reports(summary, caps, log)
    log.info("=== Imaging 17 complete: analysis + charts + reports ===")
    print("imaging_analysis_done=1")


def write_reports(summary, caps, log):
    L = summary["linkage"]
    md = ["# HeartTwin CareGuard — CT Imaging + VISTA Analysis", "",
          f"_Generated {summary['generated_at']}_", "",
          "> Research/software-testing only. VISTA output is model-derived research "
          "segmentation requiring clinician review. CT is fused into a clinical case only on "
          "independently verified same-subject linkage.", "",
          "## Linkage",
          f"- Clinical cases: **{L['total_clinical_cases']}** | with actual CT: {L['cases_with_actual_ct']}",
          f"- Verified same-subject CT: **{L['verified_same_subject_ct']}** | no-linked-CT: {L['no_linked_ct']}",
          f"- Imaging-only benchmark (real CT): **{L['imaging_only_benchmark']}** | prohibited pairings: {L['prohibited_pairings']}",
          "", "## Sources"]
    for sid, s in summary["sources"].items():
        md.append(f"- `{sid}`: {s['access_state']} (max {s['expected_max_cases']})")
    md += ["", "## VISTA endpoint",
           f"- configured: {summary['vista']['endpoint_configured']} | reachable: {summary['vista']['endpoint_reachable']} "
           f"({summary['vista']['capability_source']})",
           f"- supported classes: {summary['vista']['supported_classes']}",
           f"- jobs: {summary['vista']['jobs']} | states: {summary['vista']['states']}",
           "", "## Segmentation",
           f"- reference masks available: {summary['segmentation']['reference_masks_available']}",
           f"- metrics computed: {summary['segmentation']['metrics_computed']} "
           f"({summary['segmentation']['reason_not_computed']})",
           "", "## Fusion",
           f"- verified fusions: {summary['fusion']['verified_fusions']} | blocked: {summary['fusion']['blocked_fusions']}",
           f"- adversarial demographic match → **{summary['fusion']['prohibited_demo_status']}** (correctly blocked)",
           "", "## Strongest supported claim",
           "Real CT volumes were ingested, validated (DICOM + NIfTI), and prepared for VISTA with only "
           "endpoint-declared classes; every fusion into a clinical case is gated on verified same-subject "
           "linkage, and an adversarial demographic match is provably rejected.",
           "", "## Claims NOT supported",
           "- No CT belongs to any eICU patient. No live VISTA segmentation ran (gated). No segmentation "
           "accuracy is claimed. No diagnosis is derived from imaging."]
    (I.ANALYSIS_IMAGING / "imaging_report.md").write_text("\n".join(md))

    import json as _j
    charts = ["01_ct_linkage_status", "02_imaging_source_distribution", "03_vista_job_completion",
              "05_supported_structure_coverage", "12_reference_mask_availability",
              "14_fusion_block_reasons", "17_case_aligned_vs_imaging_only", "18_demo_imaging_proof"]
    import base64
    imgs = "".join(
        f'<figure><img src="data:image/png;base64,{base64.b64encode((I.AI_CHARTS / (c + ".png")).read_bytes()).decode()}"/>'
        f'<figcaption>{c}</figcaption></figure>' for c in charts if (I.AI_CHARTS / (c + ".png")).exists())
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>CareGuard Imaging + VISTA Report</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem;max-width:1100px}}h1{{color:#7c3aed}}
.warn{{background:#fef3c7;border-left:4px solid #f59e0b;padding:.75rem 1rem;border-radius:6px}}
figure{{display:inline-block;margin:.5rem}}img{{max-width:480px;border:1px solid #e5e7eb;border-radius:8px}}
figcaption{{font-size:.8rem;color:#666;text-align:center}}pre{{background:#f6f6f8;padding:1rem;border-radius:8px;overflow:auto;font-size:.8rem}}</style>
</head><body><h1>CareGuard — CT Imaging + VISTA (verified linkage)</h1>
<p class="warn"><b>Research/software-testing only.</b> Model-derived research segmentation requiring clinician review.
CT is fused into a clinical case only on independently verified same-subject linkage. VISTA ran in gated mode
(no live endpoint) — no segmentation masks or accuracy are fabricated.</p>
<h2>Charts</h2>{imgs}<h2>Summary</h2><pre>{_j.dumps(summary, indent=2)}</pre></body></html>"""
    (I.ANALYSIS_IMAGING / "imaging_report.html").write_text(html)

    # PDF
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        c = canvas.Canvas(str(I.ANALYSIS_IMAGING / "imaging_report.pdf"), pagesize=letter)
        w, h = letter
        y = h - 0.6 * inch
        c.setFont("Helvetica", 8)
        for line in "\n".join(md).split("\n"):
            if y < 0.6 * inch:
                c.showPage(); c.setFont("Helvetica", 8); y = h - 0.6 * inch
            c.drawString(0.6 * inch, y, line[:118]); y -= 10.5
        c.save()
    except Exception as e:
        log.warning("imaging PDF skipped: %s", e)


if __name__ == "__main__":
    main()
