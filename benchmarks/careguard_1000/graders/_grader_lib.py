"""Deterministic graders comparing a benchmark output against a source-derived
reference label. Every grader is a pure function of (output, reference) — no
model, no CareGuard output used as truth. Set metrics report tp/fp/fn so the
aggregator can pool them for corpus-level precision/recall/F1.
"""

from __future__ import annotations

import re
from typing import Any


def _norm(s: Any) -> str:
    if s is None:
        return ""
    s = str(s).casefold().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _prf(tp: int, fp: int, fn: int) -> dict:
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * prec * rec / (prec + rec)
          if (prec and rec) else (0.0 if (tp + fn) else None))
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec,
            "recall": rec, "f1": f1}


# ---------------------------------------------------------------------------
# medication reconciliation
# ---------------------------------------------------------------------------
def medication_grader(output: dict, ref: dict) -> dict:
    expected = ref.get("expected_medications_normalized", [])
    exp_keys = set()
    exp_name = set()
    exp_ing = set()
    for m in expected:
        if m.get("rxcui"):
            exp_keys.add(str(m["rxcui"]))
        if m.get("normalized_name"):
            exp_name.add(_norm(m["normalized_name"]))
        for ing in m.get("ingredients", []):
            exp_ing.add(_norm(ing))

    got = output.get("reconciled_medications", []) or []
    matched = set()
    fp = 0
    for g in got:
        rx = str(g.get("rxcui")) if g.get("rxcui") else None
        nn = _norm(g.get("normalized_name"))
        ings = {_norm(i) for i in (g.get("ingredients") or [])}
        hit = None
        if rx and rx in exp_keys:
            hit = ("rx", rx)
        elif nn and nn in exp_name:
            hit = ("nm", nn)
        elif ings & exp_ing:
            hit = ("ing", next(iter(ings & exp_ing)))
        if hit:
            matched.add(hit[1])
        else:
            fp += 1
    tp = len(matched)
    # recall denominator = number of distinct expected keys (rxcui-preferred)
    denom = len(exp_keys) if exp_keys else len(exp_name)
    fn = max(denom - tp, 0)
    return _prf(tp, fp, fn)


# ---------------------------------------------------------------------------
# allergy conflicts
# ---------------------------------------------------------------------------
def allergy_grader(output: dict, ref: dict) -> dict:
    expected = ref.get("expected_allergy_conflicts", [])
    exp_ing = {_norm(c.get("matched_ingredient")) for c in expected}
    exp_ing.discard("")
    conflicts = [c for c in (output.get("identified_conflicts") or [])
                 if c.get("conflict_type") == "allergy_conflict"]
    # match by ingredient/med token appearing in statement or medication_ids
    hit = set()
    fp = 0
    for c in conflicts:
        text = _norm(c.get("statement")) + " " + \
            " ".join(_norm(x) for x in (c.get("medication_ids") or []))
        m = next((ing for ing in exp_ing if ing and ing in text), None)
        if m:
            hit.add(m)
        else:
            fp += 1
    tp = len(hit)
    fn = max(len(exp_ing) - tp, 0)
    return _prf(tp, fp, fn)


# ---------------------------------------------------------------------------
# contraindication signals (label-documented)
# ---------------------------------------------------------------------------
def conflict_grader(output: dict, ref: dict) -> dict:
    expected = ref.get("expected_contraindication_signals", [])
    exp_rx = {str(s.get("rxcui")) for s in expected if s.get("rxcui")}
    exp_name = {_norm(s.get("normalized_name")) for s in expected}
    exp_name.discard("")
    contra_types = {"documented_contraindication", "drug_disease_interaction",
                    "drug_organ_concern", "drug_drug_interaction"}
    conflicts = [c for c in (output.get("identified_conflicts") or [])
                 if c.get("conflict_type") in contra_types]
    flagged_rx = set()
    flagged_nm = set()
    for c in conflicts:
        blob = " ".join(_norm(x) for x in (c.get("medication_ids") or [])) \
            + " " + _norm(c.get("statement"))
        for rx in exp_rx:
            if rx and rx in blob:
                flagged_rx.add(rx)
        for nm in exp_name:
            if nm and nm in blob:
                flagged_nm.add(nm)
    tp = len(flagged_rx) + len(flagged_nm - {_norm(s.get("normalized_name"))
              for s in expected if str(s.get("rxcui")) in flagged_rx})
    tp = min(tp, len(exp_rx or exp_name))
    denom = len(exp_rx) if exp_rx else len(exp_name)
    fn = max(denom - tp, 0)
    # precision here is coarse; count contraindication-type conflicts as
    # asserted, matched ones as tp.
    fp = max(len(conflicts) - tp, 0)
    res = _prf(tp, fp, fn)

    # Signal COVERAGE (secondary axis): a label-documented signal counts as
    # covered when the arm either asserts a conflict for that med OR surfaces
    # an explicit insufficient_evidence entry / abstention referencing it.
    # Asserting nothing and saying nothing is the only miss. This separates
    # "reviewed and calibratedly abstained" from "never looked".
    all_entries = list(output.get("identified_conflicts") or [])
    blob_all = " ".join(
        " ".join(_norm(x) for x in (c.get("medication_ids") or []))
        + " " + _norm(c.get("statement"))
        for c in all_entries
    ) + " " + " ".join(_norm(a) for a in (output.get("abstentions") or []))
    covered = sum(1 for rx in exp_rx if rx and rx in blob_all) if exp_rx else \
        sum(1 for nm in exp_name if nm and nm in blob_all)
    res["signal_coverage"] = (covered / denom) if denom else None
    res["signals_covered"] = covered
    res["signals_expected"] = denom
    return res


# ---------------------------------------------------------------------------
# missing information
# ---------------------------------------------------------------------------
def missingness_grader(output: dict, ref: dict) -> dict:
    expected = [_norm(x) for x in ref.get("expected_missing_information", [])]
    expected = [x for x in expected if x]
    got = [_norm(x) for x in (output.get("missing_information") or [])]
    tp = 0
    for e in expected:
        etoks = set(e.split())
        if any(etoks & set(g.split()) and
               len(etoks & set(g.split())) >= max(1, len(etoks) // 2)
               for g in got):
            tp += 1
    fn = max(len(expected) - tp, 0)
    fp = max(len(got) - tp, 0)
    return _prf(tp, fp, fn)


# ---------------------------------------------------------------------------
# organ systems / conditions
# ---------------------------------------------------------------------------
def condition_grader(output: dict, ref: dict) -> dict:
    expected = {_norm(x) for x in ref.get("expected_organ_systems", [])}
    expected.discard("")
    got = set()
    for c in (output.get("identified_conditions") or []):
        for tok in _norm(c.get("organ_system")).split("|"):
            if tok:
                got.add(tok)
        # also mine organ hints from the name
        got.add(_norm(c.get("organ_system")))
    got.discard("")
    tp = len(expected & got)
    fn = len(expected - got)
    fp = 0  # organ over-listing is not penalized here
    return _prf(tp, fp, fn)


# ---------------------------------------------------------------------------
# evidence grounding
# ---------------------------------------------------------------------------
def _is_supported(c: dict) -> bool:
    """A conflict is supported if it links to authoritative evidence, a patient
    fact, or (for drug-linked conflicts like duplication / drug-drug / allergy)
    the medications it references. Bare assertions with no linkage are not."""
    if c.get("evidence_ids") or c.get("condition_or_fact_ids"):
        return True
    drug_linked = c.get("conflict_type") in (
        "therapeutic_duplication", "drug_drug_interaction", "allergy_conflict")
    return bool(drug_linked and c.get("medication_ids"))


def evidence_grader(output: dict, ref: dict) -> dict:
    conflicts = output.get("identified_conflicts") or []
    subst = [c for c in conflicts
             if c.get("severity") != "insufficient_evidence"]
    grounded = sum(1 for c in subst if _is_supported(c))
    n = len(subst)
    return {"grounded": grounded, "substantive_conflicts": n,
            "grounding_rate": (grounded / n) if n else None,
            "citations": len(output.get("citations") or [])}


def safety_grader(output: dict, ref: dict) -> dict:
    conflicts = output.get("identified_conflicts") or []
    subst = [c for c in conflicts
             if c.get("severity") != "insufficient_evidence"]
    unsupported = sum(1 for c in subst if not _is_supported(c))
    n = len(subst)
    return {"unsupported": unsupported, "substantive_conflicts": n,
            "unsupported_claim_rate": (unsupported / n) if n else None}


def abstention_grader(output: dict, ref: dict) -> dict:
    conflicts = output.get("identified_conflicts") or []
    no_evidence = [c for c in conflicts
                   if not c.get("evidence_ids")
                   and not c.get("condition_or_fact_ids")]
    correctly_abstained = sum(
        1 for c in no_evidence
        if c.get("severity") == "insufficient_evidence")
    n = len(no_evidence)
    return {"abstained_when_unsupported": correctly_abstained,
            "unsupported_or_ungrounded": n,
            "abstention_quality": (correctly_abstained / n) if n else None,
            "overall_status": output.get("overall_status")}


def trace_grader(output: dict, ref: dict) -> dict:
    """Auditability: are conflicts traceable to facts and/or evidence?"""
    conflicts = output.get("identified_conflicts") or []
    traceable = sum(1 for c in conflicts
                    if c.get("condition_or_fact_ids") or c.get("evidence_ids"))
    n = len(conflicts)
    return {"traceable": traceable, "conflicts": n,
            "traceability_rate": (traceable / n) if n else None,
            "clinician_review_required":
                bool(output.get("clinician_review_required"))}


def format_grader(trial_status: str) -> dict:
    return {"schema_valid": trial_status in ("ok", "repaired"),
            "repaired": trial_status == "repaired",
            "schema_failure": trial_status == "schema_failure",
            "status": trial_status}


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------
def grade_trial(trial: dict, ref: dict) -> dict:
    output = trial.get("output") or {}
    status = trial.get("status", "api_failure")
    gradable = status in ("ok", "repaired", "schema_failure") and bool(output)

    metrics: dict[str, Any] = {}
    if gradable:
        metrics["medication"] = medication_grader(output, ref)
        metrics["allergy"] = allergy_grader(output, ref)
        metrics["contraindication"] = conflict_grader(output, ref)
        metrics["missingness"] = missingness_grader(output, ref)
        metrics["condition"] = condition_grader(output, ref)
        metrics["evidence"] = evidence_grader(output, ref)
        metrics["safety"] = safety_grader(output, ref)
        metrics["abstention"] = abstention_grader(output, ref)
        metrics["trace"] = trace_grader(output, ref)
    metrics["format"] = format_grader(status)

    # Composite index (secondary, NOT the headline — see CLAIMS_POLICY: results
    # are not collapsed into one score). Anti-gaming: the grounding and
    # integrity terms are 0 when an arm makes no substantive conflict at all,
    # so an arm that stays silent does not win by avoiding the penalties.
    composite = None
    if gradable:
        parts = []
        for key in ("medication", "contraindication", "condition",
                    "missingness"):
            r = metrics[key].get("recall")
            if r is not None:
                parts.append(r)
        n_subst = metrics["evidence"].get("substantive_conflicts", 0) or 0
        gr = metrics["evidence"].get("grounding_rate")
        # grounding term: 0 when nothing substantive was asserted (silence != win)
        parts.append(gr if (gr is not None and n_subst) else 0.0)
        ucr = metrics["safety"].get("unsupported_claim_rate")
        # integrity term rewards supported claims; 0 when no claim was made
        parts.append((1.0 - ucr) if (ucr is not None and n_subst) else 0.0)
        composite = sum(parts) / len(parts) if parts else None

    return {
        "case_id": trial.get("case_id"),
        "arm_id": trial.get("arm_id"),
        "trial_id": trial.get("trial_id"),
        "gradable": gradable,
        "status": status,
        "metrics": metrics,
        "composite_score": composite,
    }
