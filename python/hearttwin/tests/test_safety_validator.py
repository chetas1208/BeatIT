"""Tests for the unified assistant safety validator (Wave 2, Agent 10).

Covers:
- classify_request_safety blocks emergency/diagnosis/treatment requests,
  both via the real intake_agent.py rule classifier it reuses and via the
  supplemental patterns this module adds for phrasings intake_agent misses.
- classify_request_safety does not block a normal informational question.
- validate_numeric_claims catches a fabricated/mismatched numeric claim and
  passes a correct, matching one.
- check_output_safety is a strict union of BOTH original blocklists
  (copilot.py's _OUTPUT_RED_FLAGS and careguard/copilot_agent.py's _BLOCK) —
  one test case targets each source, proving neither was dropped.
- A tripwire test that fails loudly if either source blocklist's size changes
  without a human reviewing whether this validator's union still holds.
- REQUIRED_SAFETY_DISCLAIMER matches the exact disclaimer text AGENTS.md
  requires on every response (python/hearttwin/safety.py DISCLAIMER).
"""

from __future__ import annotations

from python.hearttwin.assistant.safety_validator import (
    REQUIRED_SAFETY_DISCLAIMER,
    check_output_safety,
    classify_request_safety,
    validate_numeric_claims,
)
from python.hearttwin.careguard.copilot_agent import _BLOCK as _CAREGUARD_BLOCK
from python.hearttwin.copilot import _OUTPUT_RED_FLAGS
from python.hearttwin.safety import CORE_SAFETY_PHRASE, DISCLAIMER


# ---------------------------------------------------------------------------
# (a) classify_request_safety blocks emergency / diagnosis / treatment
# ---------------------------------------------------------------------------


def test_classify_blocks_emergency_request_via_real_intake_rules() -> None:
    # Same phrasing style as test_intake_agent.py::test_intake_blocks_emergency_request.
    decision = classify_request_safety(
        "I'm having chest pain and shortness of breath, am I having a heart attack?"
    )
    assert decision.blocked is True
    assert decision.category == "emergency"
    assert decision.reason
    assert decision.requires_tool_grounding is False


def test_classify_blocks_diagnosis_request_via_real_intake_rules() -> None:
    # Same phrasing style as test_intake_agent.py::test_intake_blocks_diagnosis_request.
    decision = classify_request_safety("Based on my ECG, do I have atrial fibrillation?")
    assert decision.blocked is True
    assert decision.category == "diagnosis_request"


def test_classify_blocks_treatment_request_via_real_intake_rules() -> None:
    # Same phrasing style as test_intake_agent.py::test_intake_blocks_treatment_request.
    decision = classify_request_safety(
        "Please prescribe medication for this patient and set a treatment plan."
    )
    assert decision.blocked is True
    assert decision.category == "treatment_request"


def test_classify_blocks_supplemental_emergency_not_covered_by_intake_agent() -> None:
    # Deliberately avoids every intake_agent.py emergency keyword ("heart
    # attack", "emergency", "triage", "911", "ambulance", "ER") to prove this
    # is genuinely new, additive coverage, not a restatement of an existing hit.
    text = "I have crushing chest pain right now and I can't breathe."
    decision = classify_request_safety(text)
    assert decision.blocked is True
    assert decision.category == "emergency"


def test_classify_blocks_supplemental_treatment_not_covered_by_intake_agent() -> None:
    # Avoids intake_agent.py's treatment keywords ("medic", "drug", "dos*",
    # "prescrib*", "treat*").
    decision = classify_request_safety("What pill should I take for this?")
    assert decision.blocked is True
    assert decision.category == "treatment_request"


def test_classify_blocks_supplemental_diagnosis_not_covered_by_intake_agent() -> None:
    # Avoids intake_agent.py's diagnosis keywords ("diagnos*", "do i have",
    # "what do i have", "what disease", "is this a condition/illness").
    decision = classify_request_safety("What's wrong with me?")
    assert decision.blocked is True
    assert decision.category == "diagnosis_request"


# ---------------------------------------------------------------------------
# (b) normal informational question is not blocked
# ---------------------------------------------------------------------------


def test_classify_allows_normal_educational_question() -> None:
    decision = classify_request_safety("Explain how ejection fraction is calculated.")
    assert decision.blocked is False
    assert decision.category == "normal"
    assert decision.reason is None


def test_classify_marks_grounded_intents_for_tool_grounding() -> None:
    decision = classify_request_safety("Run the operation simulation for this case.")
    assert decision.blocked is False
    assert decision.requires_tool_grounding is True


# ---------------------------------------------------------------------------
# (c) / (d) numeric claim gate
# ---------------------------------------------------------------------------


def test_validate_numeric_claims_catches_fabricated_ef_mismatch() -> None:
    canonical_payload = {"ejection_fraction_pct": 45.0}
    result = validate_numeric_claims("The simulated EF is 60%.", canonical_payload)
    assert result.valid is False
    assert len(result.mismatches) == 1
    mismatch = result.mismatches[0]
    assert mismatch.metric == "EF"
    assert mismatch.claimed_value == 60.0
    assert mismatch.canonical_value == 45.0


def test_validate_numeric_claims_passes_matching_claim() -> None:
    canonical_payload = {"ejection_fraction_pct": 45.0}
    result = validate_numeric_claims("The simulated ejection fraction is 45%.", canonical_payload)
    assert result.valid is True
    assert result.mismatches == []


def test_validate_numeric_claims_tolerates_small_rounding() -> None:
    canonical_payload = {"ejection_fraction_pct": 45.3}
    result = validate_numeric_claims("Simulated EF is 45%.", canonical_payload)
    assert result.valid is True


def test_validate_numeric_claims_flags_unsupported_metric_not_in_canonical_payload() -> None:
    # cardiac output is claimed but never present in canonical_payload at all.
    canonical_payload = {"ejection_fraction_pct": 45.0}
    result = validate_numeric_claims("Cardiac output is 4.8 L/min.", canonical_payload)
    assert result.valid is False
    assert any(m.metric == "CO" and m.canonical_value is None for m in result.mismatches)


# ---------------------------------------------------------------------------
# (e) check_output_safety is a union of BOTH original blocklists
# ---------------------------------------------------------------------------


def test_check_output_safety_catches_copilot_red_flag_term() -> None:
    # Drawn directly from copilot.py's _OUTPUT_RED_FLAGS.
    decision = check_output_safety("Based on this, I recommend you take a beta blocker.")
    assert decision.blocked is True
    assert any(term.startswith("copilot:") for term in decision.matched_terms)


def test_check_output_safety_catches_careguard_block_term() -> None:
    # Drawn directly from careguard/copilot_agent.py's _BLOCK — a phrasing
    # copilot.py's own _OUTPUT_RED_FLAGS list does not contain.
    decision = check_output_safety("Well, what dose do you usually take?")
    assert decision.blocked is True
    assert any(term.startswith("careguard:") for term in decision.matched_terms)


def test_check_output_safety_allows_clean_simulation_text() -> None:
    decision = check_output_safety(
        f"{CORE_SAFETY_PHRASE} Simulated ejection fraction is 45% based on extracted values."
    )
    assert decision.blocked is False
    assert decision.matched_terms == []


def test_check_output_safety_source_lists_have_not_silently_grown() -> None:
    """Tripwire: fails loudly if either source blocklist changes size.

    This validator live-imports both lists (never copy-pastes them), so a
    same-length change is auto-covered. A LENGTH change means a human added
    or removed entries in one of the two original files and must confirm the
    union in check_output_safety's docstring/design note still reflects
    reality before this snapshot is updated.
    """
    assert len(_OUTPUT_RED_FLAGS) == 14, (
        "python/hearttwin/copilot.py _OUTPUT_RED_FLAGS changed size — review "
        "python/hearttwin/assistant/safety_validator.py::check_output_safety "
        "and docs/assistant/wave2/safety-validation.md, then update this snapshot."
    )
    assert len(_CAREGUARD_BLOCK) == 8, (
        "python/hearttwin/careguard/copilot_agent.py _BLOCK changed size — review "
        "python/hearttwin/assistant/safety_validator.py::check_output_safety "
        "and docs/assistant/wave2/safety-validation.md, then update this snapshot."
    )


# ---------------------------------------------------------------------------
# (f) REQUIRED_SAFETY_DISCLAIMER matches the existing disclaimer text
# ---------------------------------------------------------------------------


def test_required_safety_disclaimer_matches_existing_disclaimer_text() -> None:
    assert REQUIRED_SAFETY_DISCLAIMER == DISCLAIMER
    assert CORE_SAFETY_PHRASE in REQUIRED_SAFETY_DISCLAIMER
    assert "Educational cardiac simulation only" in REQUIRED_SAFETY_DISCLAIMER
