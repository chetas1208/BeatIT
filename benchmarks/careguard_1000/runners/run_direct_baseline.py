#!/usr/bin/env python3
"""Run a direct model arm (A-D) over a set of cases.

Arms:
  sonnet_45_case_only          Sonnet 4.5, canonical packet only
  sonnet_46_case_only          Sonnet 4.6, canonical packet only
  sonnet_45_evidence_grounded  Sonnet 4.5, canonical packet + evidence packet
  sonnet_46_evidence_grounded  Sonnet 4.6, canonical packet + evidence packet

The only intended difference between 4.5 and 4.6 arms is the model id; between
case-only and evidence-grounded arms is the presence of the evidence packet.
Resumable (skips trials already recorded) and cost-guarded (aborts before
exceeding config max_cost_usd unless raised).
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from _bench_common import (  # noqa: E402
    CASES_DIR, RESULTS_DIR, append_jsonl, get_api_key, load_config,
    load_prompt, read_jsonl,
)
from _case_facts import load_case_facts  # noqa: E402
from _packets import build_canonical_packet, build_evidence_packet  # noqa: E402
from _model_arm import run_model_trial  # noqa: E402

ARM_SPEC = {
    "sonnet_45_case_only": ("sonnet_45", "case_only"),
    "sonnet_46_case_only": ("sonnet_46", "case_only"),
    "sonnet_45_evidence_grounded": ("sonnet_45", "evidence"),
    "sonnet_46_evidence_grounded": ("sonnet_46", "evidence"),
}


def _prompts_for(mode: str):
    if mode == "case_only":
        return (load_prompt("direct_case_only_system.txt"),
                load_prompt("direct_case_only_user.txt"))
    return (load_prompt("direct_evidence_grounded_system.txt"),
            load_prompt("direct_evidence_grounded_user.txt"))


def build_user_prompt(mode: str, user_tmpl: str, cid: str) -> str:
    facts = load_case_facts(CASES_DIR / cid)
    packet = build_canonical_packet(facts, CASES_DIR / cid)
    packet_json = json.dumps(packet, indent=1, default=str)
    if mode == "evidence":
        ev = build_evidence_packet(facts)
        return user_tmpl.format(
            case_packet_json=packet_json,
            evidence_packet_json=json.dumps(ev, indent=1, default=str),
        )
    return user_tmpl.format(case_packet_json=packet_json)


def main() -> int:
    import pandas as pd

    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=list(ARM_SPEC))
    ap.add_argument("--cases", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--max-cost-usd", type=float, default=None,
                    help="override config cap for this arm")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore existing results and restart the arm file")
    args = ap.parse_args()

    import anthropic
    cfg = load_config("benchmark")
    models_cfg = load_config("models")
    model_key, mode = ARM_SPEC[args.arm]
    model_id = models_cfg["models"][model_key]["id"]

    cap = (args.max_cost_usd if args.max_cost_usd is not None
           else float(cfg.get("max_cost_usd", 500)))
    max_tokens = int(cfg.get("max_tokens", 6000))
    timeout = int(cfg.get("timeout_seconds", 120))
    max_retries = int(cfg.get("max_retries", 4))
    concurrency = int(cfg.get("concurrency", 4))

    if args.cases:
        case_ids = [c.strip() for c in args.cases.split(",") if c.strip()]
    else:
        idx = pd.read_parquet(RESULTS_DIR / "case_index.parquet")
        case_ids = idx[idx["status"].isin(
            ["eligible", "eligible_with_warning"])]["case_id"].tolist()
        if args.limit:
            case_ids = case_ids[:args.limit]

    out_path = RESULTS_DIR / "raw" / f"{args.arm}.ndjson"
    raw_dir = RESULTS_DIR / "raw" / "transcripts" / args.arm
    if args.fresh:
        out_path.unlink(missing_ok=True)

    # Resume: which (case, trial) are already done?
    done = set()
    prior_cost = 0.0
    for r in read_jsonl(out_path):
        done.add((r.get("case_id"), r.get("trial_id")))
        prior_cost += float(r.get("cost_usd", 0) or 0)

    work = []
    for cid in case_ids:
        for t in range(args.trials):
            tid = f"t{t}"
            if (cid, tid) not in done:
                work.append((cid, tid))

    print(f"Arm {args.arm}  model={model_id}  mode={mode}")
    print(f"  cases={len(case_ids)} trials={args.trials} "
          f"to_do={len(work)} already_done={len(done)}")
    print(f"  prior_cost=${prior_cost:.2f}  cap=${cap:.2f}")

    if not work:
        print("  nothing to do.")
        return 0

    client = anthropic.Anthropic(api_key=get_api_key())
    system_prompt, user_tmpl = _prompts_for(mode)

    running_cost = prior_cost
    n_ok = n_repaired = n_schema = n_api = 0
    cost_lock = __import__("threading").Lock()
    aborted = False

    def do_one(cid: str, tid: str) -> dict:
        up = build_user_prompt(mode, user_tmpl, cid)
        return run_model_trial(
            client=client, model_id=model_id, arm_id=args.arm,
            case_id=cid, trial_id=tid, system_prompt=system_prompt,
            user_prompt=up, max_tokens=max_tokens, max_retries=max_retries,
            timeout_seconds=timeout, store_raw_dir=raw_dir,
        )

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(do_one, cid, tid): (cid, tid) for cid, tid in work}
        for i, fut in enumerate(as_completed(futs), 1):
            cid, tid = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:
                rec = {"case_id": cid, "arm_id": args.arm, "trial_id": tid,
                       "model_id": model_id, "status": "api_failure",
                       "error_type": type(exc).__name__, "cost_usd": 0.0}
            append_jsonl(out_path, rec)
            st = rec.get("status")
            n_ok += st == "ok"
            n_repaired += st == "repaired"
            n_schema += st == "schema_failure"
            n_api += st == "api_failure"
            with cost_lock:
                running_cost += float(rec.get("cost_usd", 0) or 0)
            if i % 20 == 0 or i == len(work):
                print(f"  [{i}/{len(work)}] ok={n_ok} repaired={n_repaired} "
                      f"schema_fail={n_schema} api_fail={n_api} "
                      f"cost=${running_cost:.2f}")
            if running_cost > cap and not aborted:
                aborted = True
                print(f"  !! cost cap ${cap:.2f} exceeded (${running_cost:.2f}) "
                      f"— cancelling remaining work")
                for f2 in futs:
                    f2.cancel()
                break

    summary = {
        "arm": args.arm, "model_id": model_id, "mode": mode,
        "completed": n_ok + n_repaired + n_schema,
        "ok": n_ok, "repaired": n_repaired, "schema_failure": n_schema,
        "api_failure": n_api, "cost_usd": round(running_cost, 4),
        "aborted_on_cost": aborted,
    }
    (RESULTS_DIR / "raw" / f"{args.arm}.summary.json").write_text(
        json.dumps(summary, indent=2))
    print(f"\n{json.dumps(summary, indent=2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
