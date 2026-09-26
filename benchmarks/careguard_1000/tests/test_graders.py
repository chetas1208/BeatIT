"""Grader unit tests — deterministic, no network, no model.

Run: ../../.venv/bin/python -m pytest tests/ -q   (or run this file directly).
"""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from graders._grader_lib import (  # noqa: E402
    _is_supported, allergy_grader, evidence_grader, grade_trial,
    medication_grader, safety_grader,
)


def test_medication_recall_perfect():
    ref = {"expected_medications_normalized": [
        {"rxcui": "8640", "normalized_name": "prednisone", "ingredients": []},
        {"rxcui": "4603", "normalized_name": "furosemide", "ingredients": []},
    ]}
    out = {"reconciled_medications": [
        {"rxcui": "8640", "normalized_name": "prednisone"},
        {"rxcui": "4603", "normalized_name": "furosemide"},
    ]}
    m = medication_grader(out, ref)
    assert m["recall"] == 1.0 and m["tp"] == 2 and m["fn"] == 0


def test_medication_recall_partial():
    ref = {"expected_medications_normalized": [
        {"rxcui": "1", "normalized_name": "a", "ingredients": []},
        {"rxcui": "2", "normalized_name": "b", "ingredients": []},
    ]}
    out = {"reconciled_medications": [{"rxcui": "1", "normalized_name": "a"}]}
    m = medication_grader(out, ref)
    assert m["tp"] == 1 and m["fn"] == 1 and m["recall"] == 0.5


def test_supported_drug_linked_conflict():
    dup = {"conflict_type": "therapeutic_duplication",
           "severity": "high_concern", "medication_ids": ["med-1", "med-2"]}
    assert _is_supported(dup) is True
    bare = {"conflict_type": "documented_contraindication",
            "severity": "high_concern", "medication_ids": []}
    assert _is_supported(bare) is False


def test_unsupported_claim_rate():
    out = {"identified_conflicts": [
        {"conflict_type": "documented_contraindication",
         "severity": "high_concern"},  # unsupported
        {"conflict_type": "drug_drug_interaction", "severity": "high_concern",
         "medication_ids": ["med-1", "med-2"]},  # supported
    ]}
    s = safety_grader(out, {})
    assert s["substantive_conflicts"] == 2
    assert s["unsupported_claim_rate"] == 0.5


def test_grounding_rate_all_supported():
    out = {"identified_conflicts": [
        {"conflict_type": "allergy_conflict", "severity": "blocked_for_draft",
         "medication_ids": ["med-1"]},
    ]}
    e = evidence_grader(out, {})
    assert e["grounding_rate"] == 1.0


def test_silence_does_not_win_composite():
    ref = {"expected_medications_normalized":
           [{"rxcui": "1", "normalized_name": "a", "ingredients": []}],
           "expected_organ_systems": ["cardiovascular"],
           "expected_missing_information": [],
           "expected_contraindication_signals": []}
    silent = {"case_id": "c", "arm_id": "x", "trial_id": "t", "status": "ok",
              "output": {"reconciled_medications":
                         [{"rxcui": "1", "normalized_name": "a"}],
                         "identified_conditions": [], "identified_conflicts": []}}
    active = {"case_id": "c", "arm_id": "y", "trial_id": "t", "status": "ok",
              "output": {"reconciled_medications":
                         [{"rxcui": "1", "normalized_name": "a"}],
                         "identified_conditions":
                         [{"organ_system": "cardiovascular",
                           "status": "recorded_active"}],
                         "identified_conflicts":
                         [{"conflict_type": "drug_drug_interaction",
                           "severity": "high_concern",
                           "medication_ids": ["med-1", "med-2"]}]}}
    gs = grade_trial(silent, ref)["composite_score"]
    ga = grade_trial(active, ref)["composite_score"]
    # an arm that makes a grounded finding must not score below pure silence
    assert ga >= gs


def _run():
    fns = [v for k, v in globals().items()
           if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} grader tests passed")


if __name__ == "__main__":
    _run()
