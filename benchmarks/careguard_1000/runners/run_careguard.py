#!/usr/bin/env python3
"""Run the CareGuard arm (full) and its ablations over a set of cases.

Arm E is the production deterministic medication-safety engine
(build_multimorbidity_output) run offline — no network, no paid model calls.
Its output is mapped into the common benchmark schema. Ablations are principled
deterministic transforms of the SAME engine run (one engine call per case),
each disabling exactly one component so its contribution is measurable:

  careguard_full                            all components
  careguard_no_critic                       include critic-suppressed conflicts
  careguard_no_retrieval                    demote evidence-backed conflicts
  careguard_no_multimorbidity               drop cross-organ conflicts
  careguard_no_deterministic_conflict_engine  drop all conflict assertions

Usage:
  run_careguard.py --arm careguard_full --limit 50
  run_careguard.py --arm all --cases case-000001,case-000002
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
REPO_ROOT = BENCH.parent.parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(REPO_ROOT))  # for `python.hearttwin.careguard`

from _bench_common import (  # noqa: E402
    CASES_DIR, RESULTS_DIR, append_jsonl, load_config,
)

CARDIAC_SYSTEMS = {
    "cardiovascular", "cardiac", "cardiovascular_context", "circulatory",
    "hypertension", "arrhythmia", "heart",
}

_CG = None


def _cg():
    """Lazy-import CareGuard modules."""
    global _CG
    if _CG is None:
        from python.hearttwin.careguard import case_loader
        from python.hearttwin.careguard.fhir import parser, normalizer
        from python.hearttwin.careguard.risk.signals import extract_signals
        from python.hearttwin.careguard.agents.medication_safety_agent import (
            build_multimorbidity_output,
        )
        from python.hearttwin.careguard.schemas import CareGuardContext
        _CG = dict(
            case_loader=case_loader, parser=parser, normalizer=normalizer,
            extract_signals=extract_signals,
            build_multimorbidity_output=build_multimorbidity_output,
            CareGuardContext=CareGuardContext,
        )
    return _CG


def run_engine(case_id: str) -> dict:
    cg = _cg()
    loaded = cg["case_loader"].load_case(case_id)
    parsed = cg["parser"].parse_bundle(loaded["bundle"])
    pc = cg["normalizer"].build_patient_context(case_id, parsed)
    signals = cg["extract_signals"](pc)
    ctx = cg["CareGuardContext"](
        run_id=f"bench-{case_id}", case_id=case_id,
        clinical_question="medication safety review",
        facts=parsed.facts,
        prior_stage_outputs={
            "patient_context": pc.model_dump(),
            "citations": [],
            "report_texts": loaded.get("report_texts", []),
        },
    )
    return cg["build_multimorbidity_output"](ctx, pc, signals).model_dump()


# ---------------------------------------------------------------------------
# Mapping CareGuard engine output -> benchmark schema
# ---------------------------------------------------------------------------
_CT = {  # CareGuard conflict_type -> benchmark enum (identity where shared)
    "documented_contraindication": "documented_contraindication",
    "drug_drug_interaction": "drug_drug_interaction",
    "drug_disease_interaction": "drug_disease_interaction",
    "drug_organ_concern": "drug_organ_concern",
    "drug_organ_interaction": "drug_organ_concern",
    "allergy_conflict": "allergy_conflict",
    "therapeutic_duplication": "therapeutic_duplication",
    "monitoring_gap": "monitoring_gap",
    "insufficient_evidence": "insufficient_evidence",
}
_SEV = {
    "blocked_for_draft": "blocked_for_draft",
    "high_concern": "high_concern",
    "caution": "caution",
    "informational": "informational",
    "insufficient_evidence": "insufficient_evidence",
}


def _med_idmap(d: dict) -> dict:
    """Engine medication_id (opaque hash) -> reference-namespace fact id.

    The reference labels key medication facts as ``med-<rxcui>``. The engine's
    conflict records reference its own opaque per-run medication ids, so grader
    matching needs this translation. Pure id-namespace alignment — no content
    is added or removed.
    """
    m: dict[str, str] = {}
    for x in d.get("reconciled_active_medications") or []:
        mid = x.get("medication_id")
        if not mid:
            continue
        rx = x.get("rxcui")
        m[mid] = f"med-{rx}" if rx else mid
    return m


def _map_conflict(c: dict, idmap: dict | None = None) -> dict:
    idmap = idmap or {}
    med_ids = list(c.get("interacting_medication_ids") or [])
    if c.get("proposed_medication_id"):
        med_ids = [c["proposed_medication_id"]] + med_ids
    med_ids = [idmap.get(m, m) for m in med_ids]
    ev_ids = [e.get("evidence_id") for e in (c.get("authoritative_evidence") or [])
              if e.get("evidence_id")]
    return {
        "conflict_type": _CT.get(c.get("conflict_type"), "insufficient_evidence"),
        "severity": _SEV.get(c.get("severity"), "insufficient_evidence"),
        "medication_ids": med_ids,
        "condition_or_fact_ids": list(c.get("patient_fact_ids") or []),
        "statement": c.get("clinical_statement") or c.get("headline") or "",
        "evidence_ids": ev_ids,
        "requires_clinician_confirmation":
            bool(c.get("requires_clinician_confirmation", True)),
        "confidence": float(c.get("confidence") or 0.0),
    }


def _map_conditions(d: dict) -> list[dict]:
    out = []
    for c in d.get("confirmed_conditions") or []:
        out.append({
            "normalized_name": c.get("display") or c.get("code") or "",
            "organ_system": (c.get("display") or "").split("|")[0],
            "status": c.get("status") or "recorded_active",
            "source_fact_ids": [c.get("fact_id")] if c.get("fact_id") else [],
            "confidence": 1.0,
        })
    for c in d.get("historical_conditions") or []:
        out.append({
            "normalized_name": c.get("display") or c.get("code") or "",
            "organ_system": (c.get("display") or "").split("|")[0],
            "status": "recorded_historical",
            "source_fact_ids": [c.get("fact_id")] if c.get("fact_id") else [],
            "confidence": 1.0,
        })
    for m in d.get("report_mentions_requiring_confirmation") or []:
        out.append({
            "normalized_name": m.get("display") or m.get("text") or "",
            "organ_system": "",
            "status": "possible_report_mention",
            "source_fact_ids": [], "confidence": 0.5,
        })
    return out


def _map_meds(d: dict) -> list[dict]:
    out = []
    for m in d.get("reconciled_active_medications") or []:
        out.append({
            "original_text": m.get("original_text") or "",
            "normalized_name": m.get("normalized_name"),
            "rxcui": m.get("rxcui"),
            "ingredients": list(m.get("ingredients") or []),
            "status": m.get("status") or "",
            "source_fact_ids": [m.get("medication_id")]
            if m.get("medication_id") else [],
            "confidence": 1.0,
        })
    return out


def _map_alternatives(d: dict) -> list[dict]:
    out = []
    for a in d.get("alternative_candidates") or []:
        mi = a.get("medication_identity") or {}
        out.append({
            "normalized_name": mi.get("normalized_name")
            or a.get("normalized_name") or "",
            "alternative_type": a.get("alternative_type") or "",
            "reasons_considered": list(a.get("reasons_considered") or []),
            "evidence_ids": [
                e.get("evidence_id")
                for e in (a.get("guideline_evidence") or [])
                + (a.get("label_evidence") or [])
                if e.get("evidence_id")
            ],
            "remaining_conflicts": [
                c.get("conflict_id") for c in (a.get("documented_conflicts") or [])
                if isinstance(c, dict)
            ],
            "missing_information": list(a.get("missing_information") or []),
            "display_status": a.get("display_status")
            or "requires_more_information",
            "confidence": float(a.get("confidence") or 0.0),
        })
    return out


def _citations(conflicts: list[dict]) -> list[dict]:
    seen, out = set(), []
    for c in conflicts:
        for e in (c.get("authoritative_evidence") or []) + \
                 (c.get("supplemental_evidence") or []):
            eid = e.get("evidence_id")
            if not eid or eid in seen:
                continue
            seen.add(eid)
            out.append({
                "evidence_id": eid,
                "source_title": e.get("source_title") or "",
                "source_version": e.get("source_version"),
                "section": e.get("section"),
                "quoted_passage": (e.get("exact_passage")
                                   or e.get("passage") or "")[:400] or None,
            })
    return out


def map_full(d: dict, case_id: str) -> dict:
    conflicts_raw = d.get("conflicts") or []
    displayed = [c for c in conflicts_raw if c.get("can_display", True)]
    return {
        "case_id": case_id,
        "identified_conditions": _map_conditions(d),
        "reconciled_medications": _map_meds(d),
        "identified_conflicts": [_map_conflict(c, _med_idmap(d))
                                 for c in displayed],
        "missing_information": list(d.get("missing_information") or []),
        "alternative_candidates": _map_alternatives(d),
        "overall_status": d.get("overall_status") or "insufficient_evidence",
        "citations": _citations(displayed),
        "abstentions": [
            c.get("headline", "insufficient evidence")
            for c in displayed if c.get("severity") == "insufficient_evidence"
        ][:20],
        "warnings": [f.get("message", "") for f in (d.get("critic_findings") or [])
                     if isinstance(f, dict)][:20],
        "clinician_review_required": True,
        "pharmacist_review_recommended": any(
            c.get("requires_pharmacist_review") for c in displayed),
        "safety_disclaimer": d.get("safety_disclaimer") or "",
    }


# ---------------------------------------------------------------------------
# Ablation transforms (operate on the raw engine dict + the full mapping)
# ---------------------------------------------------------------------------
def transform_arm(arm: str, d: dict, case_id: str) -> dict:
    conflicts_raw = d.get("conflicts") or []

    if arm == "careguard_full":
        return map_full(d, case_id)

    if arm == "careguard_no_critic":
        # Include ALL conflicts, even those the critic suppressed from display.
        out = map_full(d, case_id)
        out["identified_conflicts"] = [_map_conflict(c, _med_idmap(d))
                                       for c in conflicts_raw]
        out["citations"] = _citations(conflicts_raw)
        out["warnings"] = ["critic_disabled_for_ablation"]
        return out

    if arm == "careguard_no_retrieval":
        # Demote evidence-backed conflicts to insufficient_evidence; strip
        # citations. The system must abstain rather than assert from memory.
        out = map_full(d, case_id)
        new_conf = []
        for c in out["identified_conflicts"]:
            if c["evidence_ids"]:
                c = dict(c)
                c["severity"] = "insufficient_evidence"
                c["conflict_type"] = "insufficient_evidence"
                c["evidence_ids"] = []
            new_conf.append(c)
        out["identified_conflicts"] = new_conf
        out["citations"] = []
        out["overall_status"] = "insufficient_evidence"
        out["warnings"] = ["authoritative_retrieval_disabled_for_ablation"]
        return out

    if arm == "careguard_no_multimorbidity":
        # Keep only cardiac/primary conflicts; drop cross-organ ones.
        out = map_full(d, case_id)
        keep = []
        for c in out["identified_conflicts"]:
            xorgan = c["conflict_type"] in (
                "drug_disease_interaction", "drug_organ_concern")
            organs = " ".join(c["condition_or_fact_ids"]).lower()
            is_cardiac = any(k in organs for k in CARDIAC_SYSTEMS)
            if xorgan and not is_cardiac:
                continue  # cross-organ conflict a siloed review would miss
            keep.append(c)
        out["identified_conflicts"] = keep
        out["warnings"] = ["multimorbidity_reconstruction_disabled_for_ablation"]
        return out

    if arm == "careguard_no_deterministic_conflict_engine":
        # Keep reconciliation + conditions; drop all deterministic conflict
        # assertions (model-only structural review).
        out = map_full(d, case_id)
        out["identified_conflicts"] = []
        out["citations"] = []
        out["overall_status"] = "review_required"
        out["warnings"] = ["deterministic_conflict_engine_disabled_for_ablation"]
        return out

    raise ValueError(f"unknown careguard arm {arm}")


ABLATION_ARMS = [
    "careguard_full", "careguard_no_critic", "careguard_no_retrieval",
    "careguard_no_multimorbidity", "careguard_no_deterministic_conflict_engine",
]


def _now():
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> int:
    import os

    import pandas as pd

    # CareGuard's case_loader resolves data/cases relative to CWD.
    os.chdir(REPO_ROOT)

    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="careguard_full",
                    help="arm id, or 'all' for every CareGuard arm")
    ap.add_argument("--cases", default=None,
                    help="comma-separated case ids (overrides --limit)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--trial", default="t0")
    args = ap.parse_args()

    arms = ABLATION_ARMS if args.arm == "all" else [args.arm]

    if args.cases:
        case_ids = [c.strip() for c in args.cases.split(",") if c.strip()]
    else:
        idx = pd.read_parquet(RESULTS_DIR / "case_index.parquet")
        case_ids = idx[idx["status"].isin(
            ["eligible", "eligible_with_warning"])]["case_id"].tolist()
        if args.limit:
            case_ids = case_ids[:args.limit]

    print(f"CareGuard arms {arms} over {len(case_ids)} cases ...")
    out_paths = {a: RESULTS_DIR / "raw" / f"{a}.ndjson" for a in arms}
    # fresh files for this run
    for p in out_paths.values():
        p.unlink(missing_ok=True)

    ok = fail = 0
    for i, cid in enumerate(case_ids, 1):
        try:
            d = run_engine(cid)
        except Exception as exc:
            fail += 1
            for a in arms:
                append_jsonl(out_paths[a], {
                    "case_id": cid, "arm_id": a, "trial_id": args.trial,
                    "model_id": None, "status": "api_failure",
                    "error_type": type(exc).__name__,
                    "error_detail": repr(exc)[:200],
                    "output": None, "cost_usd": 0.0,
                    "latency_seconds": 0.0, "finished_at": _now(),
                })
            continue
        for a in arms:
            try:
                out = transform_arm(a, d, cid)
                append_jsonl(out_paths[a], {
                    "case_id": cid, "arm_id": a, "trial_id": args.trial,
                    "model_id": "careguard_deterministic_engine",
                    "status": "ok", "output": out,
                    "raw_output_present": True,
                    "usage": {}, "cost_usd": 0.0, "latency_seconds": 0.0,
                    "stop_reason": "end_turn", "retry_count": 0,
                    "tool_call_count": 0, "finished_at": _now(),
                })
            except Exception as exc:
                append_jsonl(out_paths[a], {
                    "case_id": cid, "arm_id": a, "trial_id": args.trial,
                    "status": "schema_failure",
                    "error_type": type(exc).__name__,
                    "output": None, "cost_usd": 0.0, "finished_at": _now(),
                })
        ok += 1
        if i % 100 == 0:
            print(f"  ... {i}/{len(case_ids)} (engine ok={ok} fail={fail})")

    print(f"\nDone. engine ok={ok} fail={fail}")
    for a, p in out_paths.items():
        print(f"  {a:44s} -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
