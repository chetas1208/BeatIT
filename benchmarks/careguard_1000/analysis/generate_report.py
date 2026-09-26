#!/usr/bin/env python3
"""Generate the benchmark report in Markdown, HTML, and PDF, plus a concise
demo-ready proof summary. Reads the aggregate + statistics JSON.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from _bench_common import RESULTS_DIR  # noqa: E402

DISCLAIMER = (
    "Research benchmark using deidentified, synthetic, or composite open-data "
    "cases. Not a clinical-validation study and not for diagnosis or treatment "
    "decisions. Where a case links a PTB-XL ECG to an eICU record, the ECG and "
    "EHR originate from different deidentified individuals and are combined "
    "only for multimodal software testing."
)

ARM_ORDER = [
    "sonnet_45_case_only", "sonnet_46_case_only",
    "sonnet_45_evidence_grounded", "sonnet_46_evidence_grounded",
    "careguard_full", "careguard_no_critic", "careguard_no_retrieval",
    "careguard_no_multimorbidity", "careguard_no_deterministic_conflict_engine",
]


def _pct(v, d=1):
    return "—" if v is None else f"{v * 100:.{d}f}%"


def _num(v, d=3):
    return "—" if v is None else f"{v:.{d}f}"


def _load(p):
    return json.loads(p.read_text()) if p.exists() else {}


def build_markdown() -> str:
    agg = _load(RESULTS_DIR / "aggregate" / "metrics.json")
    stats = _load(RESULTS_DIR / "statistics" / "statistics.json")
    subg = _load(RESULTS_DIR / "statistics" / "subgroups.json")
    fails = _load(RESULTS_DIR / "failures" / "failure_analysis.json")
    verify = _load(RESULTS_DIR / "model_verification.json")
    idx_sum = _load(RESULTS_DIR / "case_index_summary.json")
    arms = [a for a in ARM_ORDER if a in agg]

    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = []
    L.append("# HeartTwin CareGuard — 1,000-Case Benchmark")
    L.append("")
    L.append(f"*Generated {now}*")
    L.append("")
    L.append(f"> {DISCLAIMER}")
    L.append("")

    # Model verification
    L.append("## Model verification")
    mv = verify.get("models", {})
    L.append("")
    L.append("| arm key | model id | available | display |")
    L.append("|---|---|---|---|")
    for k, e in mv.items():
        r = e.get("retrieved", {})
        L.append(f"| {k} | `{e.get('model_id')}` | "
                 f"{'yes' if e.get('available') else 'NO'} | "
                 f"{r.get('display_name', '')} |")
    L.append("")
    if idx_sum:
        L.append(f"Cases indexed: **{idx_sum.get('total_cases')}** "
                 f"(eligible for run: {idx_sum.get('eligible_for_run')}; "
                 f"with medication label evidence: "
                 f"{idx_sum.get('with_medication_evidence')}).")
        L.append("")

    # Primary metrics table
    L.append("## Primary metrics by arm (silver reference set)")
    L.append("")
    L.append("| arm | n | med recall | contra recall | organ recall | "
             "grounding | unsupported | abstention | schema valid | composite |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for a in arms:
        m = agg[a]
        L.append(
            f"| {a} | {m['n_trials']} | "
            f"{_pct(m['medication']['recall'])} | "
            f"{_pct(m['contraindication']['recall'])} | "
            f"{_pct(m['condition']['recall'])} | "
            f"{_pct(m['evidence']['mean'])} | "
            f"{_pct(m['safety']['mean'])} | "
            f"{_pct(m['abstention']['mean'])} | "
            f"{_pct(m['schema']['valid_rate'])} | "
            f"{_num(m['composite']['mean'])} |"
        )
    L.append("")

    # Operational
    L.append("## Operational metrics")
    L.append("")
    L.append("| arm | cost/case | median lat (s) | p95 lat (s) | "
             "in tok | out tok | api fail | schema fail | completion |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    for a in arms:
        o = agg[a]["operational"]
        L.append(
            f"| {a} | ${_num(o['cost_usd_per_case'], 4)} | "
            f"{_num(o['latency_median_s'], 1)} | "
            f"{_num(o['latency_p95_s'], 1)} | "
            f"{_num(o['input_tokens_mean'], 0)} | "
            f"{_num(o['output_tokens_mean'], 0)} | "
            f"{_pct(o['api_failure_rate'])} | "
            f"{_pct(o['schema_failure_rate'])} | "
            f"{_pct(o['completion_rate'])} |"
        )
    L.append("")

    # Bootstrap CIs
    L.append("## Composite score — bootstrap 95% CI")
    L.append("")
    L.append("| arm | composite mean | 95% CI | med recall | CI |")
    L.append("|---|--:|:--|--:|:--|")
    for a in arms:
        bs = stats.get("bootstrap", {}).get(a, {})
        c = bs.get("composite", {})
        mr = bs.get("medication_recall", {})
        ci = (f"[{_num(c.get('lo'))}, {_num(c.get('hi'))}]"
              if c.get("lo") is not None else "—")
        mci = (f"[{_pct(mr.get('lo'))}, {_pct(mr.get('hi'))}]"
               if mr.get("lo") is not None else "—")
        L.append(f"| {a} | {_num(c.get('mean'))} | {ci} | "
                 f"{_pct(mr.get('mean'))} | {mci} |")
    L.append("")

    # Paired comparisons
    L.append("## Paired comparisons (Wilcoxon signed-rank on per-case composite)")
    L.append("")
    L.append("| comparison | arm A | arm B | mean A | mean B | Δ | n | p-value |")
    L.append("|---|---|---|--:|--:|--:|--:|--:|")
    for name, pr in stats.get("paired", {}).items():
        c = pr["composite"]
        p = c.get("p_value")
        pstr = "—" if p is None else (f"{p:.2e}" if p < 0.001 else f"{p:.3f}")
        L.append(
            f"| {name} | {pr['arm_a']} | {pr['arm_b']} | "
            f"{_num(c.get('mean_a'))} | {_num(c.get('mean_b'))} | "
            f"{_num(c.get('mean_diff'))} | {c.get('n_paired')} | {pstr} |")
    L.append("")

    # Subgroups
    if subg:
        L.append("## Subgroup analysis (composite by medication burden)")
        L.append("")
        L.append("| arm | few (≤10) | many (11–40) | polypharmacy (≥41) |")
        L.append("|---|--:|--:|--:|")
        for a in arms:
            b = subg.get(a, {}).get("by_medication_band", {})
            def cell(k):
                d = b.get(k)
                return f"{_num(d['mean'])} (n={d['n']})" if d else "—"
            L.append(f"| {a} | {cell('few<=10')} | {cell('many_11_40')} | "
                     f"{cell('poly>=41')} |")
        L.append("")

    # Failures
    L.append("## Failure analysis")
    L.append("")
    L.append("| arm | ok | repaired | schema fail | api fail |")
    L.append("|---|--:|--:|--:|--:|")
    for a in arms:
        bs = fails.get(a, {}).get("by_status", {})
        L.append(f"| {a} | {bs.get('ok', 0)} | {bs.get('repaired', 0)} | "
                 f"{bs.get('schema_failure', 0)} | {bs.get('api_failure', 0)} |")
    L.append("")

    # Charts
    charts = sorted((RESULTS_DIR / "charts").glob("*.png"))
    if charts:
        L.append("## Charts")
        L.append("")
        for c in charts:
            L.append(f"![{c.stem}](../charts/{c.name})")
        L.append("")

    L.append("## Methodology & limitations")
    L.append("")
    L.append("See `METHODOLOGY.md`, `LIMITATIONS.md`, `CLAIMS_POLICY.md`, and "
             "`DATA_LINEAGE.md`. Primary scoring is deterministic against a "
             "source-derived (silver) reference set; no model grades itself and "
             "no system output is used as ground truth. A human-adjudicated "
             "gold subset is queued (`reference/adjudication_queue.csv`).")
    L.append("")
    return "\n".join(L)


def build_demo_summary() -> str:
    agg = _load(RESULTS_DIR / "aggregate" / "metrics.json")
    stats = _load(RESULTS_DIR / "statistics" / "statistics.json")
    arms = [a for a in ARM_ORDER if a in agg]
    L = ["# CareGuard benchmark — proof summary", "",
         f"> {DISCLAIMER}", ""]
    if "careguard_full" in agg:
        cg = agg["careguard_full"]
        L.append(f"- **CareGuard (Arm E)** graded on **{cg['n_trials']}** "
                 f"cases; composite {_num(cg['composite']['mean'])}, "
                 f"medication recall {_pct(cg['medication']['recall'])}, "
                 f"schema-valid {_pct(cg['schema']['valid_rate'])}, "
                 f"cost/case ${_num(cg['operational']['cost_usd_per_case'], 4)}.")
    for name in ("model_generation_case_only", "system_vs_model_46",
                 "ablation_conflict_engine", "ablation_retrieval"):
        pr = stats.get("paired", {}).get(name)
        if pr:
            c = pr["composite"]
            p = c.get("p_value")
            pstr = "n/a" if p is None else (f"p={p:.2e}" if p < 0.001
                                            else f"p={p:.3f}")
            L.append(f"- **{name}**: {pr['arm_a']} {_num(c.get('mean_a'))} vs "
                     f"{pr['arm_b']} {_num(c.get('mean_b'))} "
                     f"(Δ {_num(c.get('mean_diff'))}, {pstr}, "
                     f"n={c.get('n_paired')}).")
    L.append("")
    L.append("Full tables, CIs, subgroup and failure analysis in "
             "`results/reports/report.md` / `.html` / `.pdf`.")
    L.append("")
    return "\n".join(L)


def write_html(md_text: str, out: Path) -> None:
    try:
        import markdown as md
        body = md.markdown(md_text, extensions=["tables", "fenced_code"])
    except Exception:
        body = "<pre>" + md_text.replace("<", "&lt;") + "</pre>"
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>CareGuard 1,000-Case Benchmark</title>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1000px;
margin:24px auto;padding:0 20px;color:#0f172a;line-height:1.5}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px}}
th,td{{border:1px solid #e2e8f0;padding:6px 8px;text-align:left}}
th{{background:#f8fafc}} td{{text-align:right}} td:first-child{{text-align:left}}
blockquote{{background:#fef2f2;border-left:4px solid #dc2626;padding:8px 12px;
color:#7f1d1d}} img{{max-width:100%}} code{{background:#f1f5f9;padding:1px 4px}}
h1,h2{{color:#7c3aed}}
</style></head><body>{body}</body></html>"""
    out.write_text(html)


def write_pdf(md_text: str, out: Path) -> None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image)
        from reportlab.lib import colors
    except Exception as exc:
        print(f"  (PDF skipped: reportlab unavailable: {exc})")
        return

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Disc", parent=styles["Normal"],
                              textColor=colors.HexColor("#7f1d1d"),
                              backColor=colors.HexColor("#fef2f2"),
                              borderPadding=6, fontSize=8))
    doc = SimpleDocTemplate(str(out), pagesize=letter,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    flow = []
    for raw in md_text.splitlines():
        line = raw.rstrip()
        if not line:
            flow.append(Spacer(1, 4))
            continue
        if line.startswith("# "):
            flow.append(Paragraph(line[2:], styles["Title"]))
        elif line.startswith("## "):
            flow.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("> "):
            flow.append(Paragraph(line[2:], styles["Disc"]))
        elif line.startswith("|") and "---" not in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            # accumulate rows into tables
            if flow and isinstance(flow[-1], Table):
                pass  # handled below via buffer approach
            flow.append(("ROW", cells))
        elif line.startswith("!["):
            continue
        elif line.startswith("*") and line.endswith("*"):
            flow.append(Paragraph(line.strip("*"), styles["Italic"]))
        else:
            flow.append(Paragraph(line, styles["Normal"]))

    # collapse consecutive ROW tuples into Tables
    final = []
    buf = []

    def flush():
        nonlocal buf
        if buf:
            t = Table(buf, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            final.append(t)
            final.append(Spacer(1, 6))
            buf = []

    for item in flow:
        if isinstance(item, tuple) and item[0] == "ROW":
            buf.append(item[1])
        else:
            flush()
            final.append(item)
    flush()

    # append charts
    for c in sorted((RESULTS_DIR / "charts").glob("*.png")):
        try:
            final.append(Image(str(c), width=6.5 * inch, height=3.0 * inch))
            final.append(Spacer(1, 6))
        except Exception:
            pass

    doc.build(final)


def main() -> int:
    reports = RESULTS_DIR / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    md_text = build_markdown()
    (reports / "report.md").write_text(md_text)
    write_html(md_text, reports / "report.html")
    write_pdf(md_text, reports / "report.pdf")

    demo = build_demo_summary()
    (reports / "demo_summary.md").write_text(demo)
    write_html(demo, reports / "demo_summary.html")

    print("Wrote results/reports/report.{md,html,pdf} and demo_summary.{md,html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
