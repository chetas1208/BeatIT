"""Tests for the report-consistency validator (Wave 6.5).

Covers each check with a genuine violation AND a clean/correct-text pass
(false-positive avoidance matters as much as catching real violations, per
the task spec) — mirroring test_safety_validator.py's and
test_language_integrity.py's own pattern of pairing "catches X" with "does
not flag house-style Y".
"""

from __future__ import annotations

from python.hearttwin.assistant.physician_brief import DecisionSupportBundle
from python.hearttwin.assistant.report_consistency import (
    DEFAULT_EXPECTED_UNITS,
    detect_negation_reversal,
    detect_number_before_label_claims,
    detect_uncertainty_loss,
    validate_observed_derived_simulated_boundary,
    validate_report_consistency,
    validate_unit_consistency,
)
from python.hearttwin.assistant.safety_validator import validate_numeric_claims
from python.hearttwin.assistant.schemas import CanonicalProvenanceKind, ProvenanceRef
from python.hearttwin.safety import CORE_SAFETY_PHRASE

# ---------------------------------------------------------------------------
# 1. Unit consistency
# ---------------------------------------------------------------------------


def test_validate_unit_consistency_catches_genuine_unit_mismatch() -> None:
    # Cardiac output stated in "%" instead of "L/min" — validate_numeric_claims
    # would not catch this at all (it only diffs the VALUE 4.8, never the unit).
    mismatches = validate_unit_consistency(
        "The cardiac output was 4.8%.", DEFAULT_EXPECTED_UNITS
    )
    assert len(mismatches) == 1
    assert mismatches[0].metric == "CO"
    assert mismatches[0].expected_unit == "L/min"
    assert mismatches[0].found_unit == "%"


def test_validate_unit_consistency_catches_ef_reported_in_ml() -> None:
    mismatches = validate_unit_consistency("EF was 45 mL.", DEFAULT_EXPECTED_UNITS)
    assert len(mismatches) == 1
    assert mismatches[0].metric == "EF"
    assert mismatches[0].found_unit == "mL"
    assert mismatches[0].expected_unit == "%"


def test_validate_unit_consistency_passes_correct_units() -> None:
    text = "Simulated EF is 45%. Cardiac output is 4.8 L/min. Heart rate is 72 bpm."
    assert validate_unit_consistency(text, DEFAULT_EXPECTED_UNITS) == []


def test_validate_unit_consistency_no_false_positive_when_unit_absent() -> None:
    # A bare number with no unit token at all is not checked (fail safely on
    # incomplete data rather than guessing a unit was implied).
    assert validate_unit_consistency("EF is 45.", DEFAULT_EXPECTED_UNITS) == []


# ---------------------------------------------------------------------------
# 2. Negation reversal
# ---------------------------------------------------------------------------


def test_detect_negation_reversal_catches_genuine_reversal() -> None:
    source = "No evidence of pericardial effusion is seen on this study."
    generated = "The pericardial effusion is clearly present and should be monitored."
    findings = detect_negation_reversal(source, generated)
    assert len(findings) == 1
    assert "pericardial effusion" in findings[0].subject


def test_detect_negation_reversal_catches_denies_cue() -> None:
    source = "Patient denies chest pain during the recorded episode."
    generated = "Chest pain during the recorded episode was significant."
    findings = detect_negation_reversal(source, generated)
    assert any("chest pain" in f.subject for f in findings)


def test_detect_negation_reversal_no_false_positive_when_still_negated() -> None:
    source = "No evidence of pericardial effusion is seen on this study."
    generated = "There is no pericardial effusion identified, consistent with the prior study."
    assert detect_negation_reversal(source, generated) == []


def test_detect_negation_reversal_no_false_positive_when_subject_not_mentioned() -> None:
    source = "No evidence of pericardial effusion is seen on this study."
    generated = "Left ventricular function is within normal limits."
    assert detect_negation_reversal(source, generated) == []


# ---------------------------------------------------------------------------
# 3. Uncertainty loss
# ---------------------------------------------------------------------------


def test_detect_uncertainty_loss_catches_genuine_loss() -> None:
    source = "There is a possible small pericardial effusion noted on this imaging study."
    generated = "A small pericardial effusion is present on this imaging study."
    findings = detect_uncertainty_loss(source, generated)
    assert len(findings) == 1
    assert findings[0].hedge_term.lower() == "possible"


def test_detect_uncertainty_loss_catches_inconclusive_dropped() -> None:
    source = "Findings regarding the anterior wall motion abnormality are inconclusive."
    generated = "The anterior wall motion abnormality is confirmed on this study."
    findings = detect_uncertainty_loss(source, generated)
    assert len(findings) >= 1


def test_detect_uncertainty_loss_no_false_positive_when_hedge_retained() -> None:
    source = "There is a possible small pericardial effusion noted on this imaging study."
    generated = (
        "A possible small pericardial effusion remains noted on this imaging "
        "study; findings are inconclusive."
    )
    assert detect_uncertainty_loss(source, generated) == []


def test_detect_uncertainty_loss_no_false_positive_on_unrelated_sentence() -> None:
    source = "There is a possible small pericardial effusion noted on this imaging study."
    generated = "The heart rate is within normal limits."
    assert detect_uncertainty_loss(source, generated) == []


# ---------------------------------------------------------------------------
# 4. Observed / derived / simulated boundary
# ---------------------------------------------------------------------------


def test_boundary_violation_catches_derived_claimed_as_observed() -> None:
    # Real-world grounding: physician_brief.py's own design note classifies
    # get_cardiac_findings output as DERIVED (computed from simulated
    # cardiac state), never OBSERVED — exactly the scenario this check exists
    # to catch if generated prose claimed otherwise.
    violation = validate_observed_derived_simulated_boundary(
        CanonicalProvenanceKind.DERIVED,
        "This ejection fraction value was directly observed on echocardiogram.",
        "observed",
    )
    assert violation is not None
    assert violation.real_kind == "derived"
    assert violation.claimed_kind == "observed"


def test_boundary_violation_catches_via_text_fallback_when_claim_not_supplied() -> None:
    violation = validate_observed_derived_simulated_boundary(
        CanonicalProvenanceKind.SIMULATED,
        "This value was measured directly from the patient.",
        "",
    )
    assert violation is not None
    assert violation.real_kind == "simulated"
    assert violation.claimed_kind == "observed"


def test_boundary_violation_no_false_positive_when_kinds_match() -> None:
    violation = validate_observed_derived_simulated_boundary(
        CanonicalProvenanceKind.DERIVED,
        "This ejection fraction value was derived from the simulated cardiac state.",
        "derived",
    )
    assert violation is None


def test_boundary_violation_fails_safely_on_out_of_scope_kind() -> None:
    # MODEL_PRIOR doesn't map onto the observed/derived/simulated 3-way split
    # — no verdict, not a guess.
    violation = validate_observed_derived_simulated_boundary(
        CanonicalProvenanceKind.MODEL_PRIOR,
        "This value was observed directly.",
        "observed",
    )
    assert violation is None


def test_boundary_violation_fails_safely_on_ambiguous_text_fallback() -> None:
    violation = validate_observed_derived_simulated_boundary(
        CanonicalProvenanceKind.DERIVED,
        "This value was observed and also simulated in a follow-up run.",
        "",
    )
    assert violation is None


# ---------------------------------------------------------------------------
# 5. Number-before-label numeric gate fix
# ---------------------------------------------------------------------------


def test_existing_validator_misses_number_before_label_phrasing() -> None:
    # Documents the exact gap this supplemental check exists to close, without
    # touching safety_validator.py at all.
    result = validate_numeric_claims(
        "The ventricle showed 45% EF on this study.", {"ejection_fraction_pct": 60.0}
    )
    assert result.valid is True
    assert result.mismatches == []


def test_detect_number_before_label_claims_catches_the_gap() -> None:
    mismatches = detect_number_before_label_claims(
        "The ventricle showed 45% EF on this study.", {"ejection_fraction_pct": 60.0}
    )
    assert len(mismatches) == 1
    assert mismatches[0].metric == "EF"
    assert mismatches[0].claimed_value == 45.0
    assert mismatches[0].canonical_value == 60.0


def test_detect_number_before_label_claims_no_false_positive_when_matching() -> None:
    mismatches = detect_number_before_label_claims(
        "The ventricle showed 60% EF on this study.", {"ejection_fraction_pct": 60.0}
    )
    assert mismatches == []


def test_detect_number_before_label_claims_does_not_cross_sentence_boundary() -> None:
    # "45" belongs to an unrelated clause; the period breaks tight adjacency
    # so this must not be misread as an EF claim of 45.
    mismatches = detect_number_before_label_claims(
        "The patient is 45. EF is preserved.", {"ejection_fraction_pct": 60.0}
    )
    assert mismatches == []


# ---------------------------------------------------------------------------
# 6. Aggregate: validate_report_consistency
# ---------------------------------------------------------------------------


def _bundle(**overrides) -> DecisionSupportBundle:
    defaults = dict(
        question="Decision support for case demo-1",
        clinical_context={"case_id": "demo-1"},
        simulated_results=[{"metric_id": "ejection_fraction_pct", "mean": 45.0}],
        provenance=[ProvenanceRef(kind=CanonicalProvenanceKind.DERIVED, source_id="get_cardiac_findings")],
    )
    defaults.update(overrides)
    return DecisionSupportBundle(**defaults)


def test_validate_report_consistency_flags_a_combined_bad_report() -> None:
    bundle = _bundle()
    # Deliberately avoids the word "simulated" anywhere else in the text: the
    # aggregate boundary check bails (no verdict) when the whole report's
    # kind-language is ambiguous (see module docstring), so a text containing
    # both "simulated" and "observed" language would correctly NOT trigger a
    # verdict here — that is exercised separately as a fail-safe case, not a
    # bug, in test_boundary_violation_fails_safely_on_ambiguous_text_fallback.
    report_text = (
        f"{CORE_SAFETY_PHRASE} Ejection fraction is 60%. "
        "This ejection fraction value was directly observed on echocardiogram."
    )
    result = validate_report_consistency(report_text, bundle, source_texts=None)
    assert result.valid is False
    # The EF claim (60) mismatches canonical (45).
    assert any(m.metric == "EF" for m in result.numeric_mismatches)
    # The report claims "observed" for data the bundle tracks as DERIVED.
    assert any(v.claimed_kind == "observed" for v in result.boundary_violations)
    assert any("no source_texts supplied" in s for s in result.skipped_checks)


def test_validate_report_consistency_passes_clean_report_no_false_positives() -> None:
    bundle = _bundle()
    report_text = (
        f"{CORE_SAFETY_PHRASE} Simulated ejection fraction is 45%. "
        "This ejection fraction value was derived from the simulated cardiac state."
    )
    source_texts = ["No evidence of pericardial effusion is seen on this study."]
    result = validate_report_consistency(report_text, bundle, source_texts=source_texts)
    assert result.numeric_mismatches == []
    assert result.numeric_before_label_mismatches == []
    assert result.unit_mismatches == []
    assert result.negation_reversals == []
    assert result.uncertainty_loss == []
    assert result.boundary_violations == []
    assert result.output_safety.blocked is False
    assert result.valid is True


def test_validate_report_consistency_notes_skipped_checks_on_empty_bundle() -> None:
    bundle = DecisionSupportBundle(question="Decision support for case empty-1")
    result = validate_report_consistency(
        f"{CORE_SAFETY_PHRASE} No simulated data available yet.", bundle, source_texts=None
    )
    assert any("empty canonical payload" in s for s in result.skipped_checks)
    assert any("no source_texts supplied" in s for s in result.skipped_checks)


def test_validate_report_consistency_source_texts_drive_negation_check() -> None:
    bundle = _bundle()
    report_text = (
        f"{CORE_SAFETY_PHRASE} Simulated ejection fraction is 45%. "
        "The pericardial effusion is clearly present and should be monitored."
    )
    source_texts = ["No evidence of pericardial effusion is seen on this study."]
    result = validate_report_consistency(report_text, bundle, source_texts=source_texts)
    assert result.valid is False
    assert any("pericardial effusion" in n.subject for n in result.negation_reversals)
