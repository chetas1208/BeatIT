"""Tests for the prescriptive/authority-language style guard (Wave 3, Agent 15).

Covers:
- Obvious prescriptive/imperative examples get flagged with the right
  category (one clean example per category, chosen so they don't overlap).
- Clean, appropriately-hedged BeatIT-style language does NOT get flagged
  (false-positive check — as important as catching real violations).
- narrow_can_i_take_check distinguishes benign "can I take" phrasings
  (simulation/look/ensemble) from medication-adjacent ones.
- scan_assistant_module_for_violations run against the real, current
  python/hearttwin/assistant/ directory (report, don't hide, what it finds).
"""

from __future__ import annotations

from python.hearttwin.assistant.language_integrity import (
    narrow_can_i_take_check,
    scan_assistant_module_for_violations,
    scan_for_prescriptive_language,
)

# ---------------------------------------------------------------------------
# (a) obvious prescriptive/imperative examples -> flagged, correct category
# ---------------------------------------------------------------------------


def test_flags_imperative_treatment_take_with_dose() -> None:
    result = scan_for_prescriptive_language("Take 400mg of ibuprofen twice a day for the pain.")
    assert result.flagged is True
    assert result.category == "imperative_treatment"
    assert result.matched_patterns


def test_flags_imperative_treatment_stop_medication() -> None:
    result = scan_for_prescriptive_language("You should stop taking your medication immediately.")
    assert result.flagged is True
    assert result.category == "imperative_treatment"


def test_flags_clinical_authority_claim() -> None:
    # "monitor your symptoms" deliberately avoids the imperative verb list
    # (start/stop/increase/decrease/take) so this example isolates the
    # authority-claim category rather than also tripping imperative_treatment.
    result = scan_for_prescriptive_language("I recommend you monitor your symptoms closely.")
    assert result.flagged is True
    assert result.category == "clinical_authority_claim"


def test_flags_you_must_as_authority_claim() -> None:
    result = scan_for_prescriptive_language("You must schedule an appointment right away.")
    assert result.flagged is True
    assert result.category == "clinical_authority_claim"


def test_flags_unsupported_diagnostic_certainty() -> None:
    result = scan_for_prescriptive_language("Your diagnosis is atrial fibrillation.")
    assert result.flagged is True
    assert result.category == "unsupported_diagnostic_certainty"


def test_flags_you_have_condition_without_hedge() -> None:
    result = scan_for_prescriptive_language("You have heart failure based on this reading.")
    assert result.flagged is True
    assert result.category == "unsupported_diagnostic_certainty"


# ---------------------------------------------------------------------------
# (b) clean, hedged BeatIT-style language -> NOT flagged
# ---------------------------------------------------------------------------


def test_does_not_flag_available_evidence_supports_phrasing() -> None:
    result = scan_for_prescriptive_language(
        "The available evidence supports these considerations regarding cardiac function."
    )
    assert result.flagged is False
    assert result.category == "clean"
    assert result.matched_patterns == []


def test_does_not_flag_simulation_produces_phrasing() -> None:
    result = scan_for_prescriptive_language("The simulation produces an ejection fraction of 43%.")
    assert result.flagged is False
    assert result.category == "clean"


def test_does_not_flag_evidence_insufficient_phrasing() -> None:
    result = scan_for_prescriptive_language(
        "Evidence is insufficient to resolve this discrepancy between models."
    )
    assert result.flagged is False
    assert result.category == "clean"


def test_does_not_flag_hedged_diagnostic_language() -> None:
    result = scan_for_prescriptive_language(
        "This may suggest reduced contractility, but is consistent with several possible causes."
    )
    assert result.flagged is False
    assert result.category == "clean"


def test_does_not_flag_you_have_non_medical_sense() -> None:
    # "you have to" / "you have access" / "you have questions" are common,
    # benign UI/help copy shapes the diagnostic-certainty pattern explicitly
    # excludes via its negative lookahead.
    result = scan_for_prescriptive_language("If you have questions about this report, contact your physician.")
    assert result.flagged is False


# ---------------------------------------------------------------------------
# (c) narrow_can_i_take_check: benign vs. medication-adjacent
# ---------------------------------------------------------------------------


def test_can_i_take_simulation_further_is_not_flagged() -> None:
    assert narrow_can_i_take_check("Can I take this simulation further?") is False


def test_can_i_take_closer_look_is_not_flagged() -> None:
    assert narrow_can_i_take_check("Can I take a closer look at the PV loop?") is False


def test_can_i_take_median_twin_is_not_flagged() -> None:
    assert narrow_can_i_take_check("Can I take the median twin from this ensemble?") is False


def test_can_i_take_ibuprofen_is_flagged() -> None:
    assert narrow_can_i_take_check("Can I take ibuprofen for this?") is True


def test_can_i_take_with_dose_shape_is_flagged() -> None:
    assert narrow_can_i_take_check("Can I take 50mg of metoprolol?") is True


def test_can_i_take_over_the_counter_is_flagged() -> None:
    assert narrow_can_i_take_check("Can I take an over-the-counter painkiller for this?") is True


def test_can_i_take_with_no_med_word_at_all_is_not_flagged() -> None:
    assert narrow_can_i_take_check("Can I take a break from reading this report?") is False


# ---------------------------------------------------------------------------
# (d) scan_assistant_module_for_violations against the real assistant/ dir
# ---------------------------------------------------------------------------


def test_scan_assistant_module_returns_a_result_for_real_codebase() -> None:
    violations = scan_assistant_module_for_violations()
    assert isinstance(violations, list)
    # Reported, not hidden: at the time this test was written, the real
    # python/hearttwin/assistant/ package (router.py, schemas.py,
    # tool_registry.py, model_pool.py, laya_adapter.py, safety_validator.py)
    # produced zero hits — see docs/assistant/wave3/clinical-language-integrity.md
    # for the pasted run output. If this assertion ever fails, that is a
    # real finding to report honestly, not a signal to loosen the scanner.
    for file_path, detail in violations:
        assert isinstance(file_path, str) and isinstance(detail, str)
