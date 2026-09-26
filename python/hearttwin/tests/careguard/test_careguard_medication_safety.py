"""Golden + unit tests for the Multimorbidity Medication Safety engine."""

from __future__ import annotations

from python.hearttwin.careguard.medications import (
    alternative_engine,
    conflict_engine,
    medication_reconciler,
    rxnorm_client,
    safety_critic,
    source_registry,
)
from python.hearttwin.careguard.medications.schemas import MedicationIdentity
from python.hearttwin.careguard.reports import condition_mention_extractor as cme


def _ident(name, rxcui=None, ingredients=None, mid="m1"):
    return MedicationIdentity(
        medication_id=mid, original_text=name, rxcui=rxcui,
        ingredients=ingredients or [name.split()[0]], status="active",
        source_resource_type="MedicationStatement",
    )


_RENAL_SIGNALS = {"reduced_egfr": True, "missing_potassium": True, "pregnancy_recorded": False,
                  "allergen_terms": [], "allergy_fact_ids": [], "renal_fact_ids": ["egfr-1"]}
_CLEAN_SIGNALS = {"reduced_egfr": False, "missing_potassium": False, "pregnancy_recorded": False,
                  "allergen_terms": [], "allergy_fact_ids": [], "renal_fact_ids": []}


# ---- normalization -------------------------------------------------------
def test_rxnorm_uses_coded_rxcui_and_preserves_text():
    n = rxnorm_client.normalize(name="spironolactone 25 mg tablet", coded_rxcui="9997")
    assert n["rxcui"] == "9997" and n["resolved"] and n["original_text"].startswith("spironolactone")


def test_fictitious_drug_not_assigned_pharmacology():
    n = rxnorm_client.normalize(name="florbinzamax")
    assert n["rxcui"] is None and n["resolved"] is False


def test_duplicate_active_ingredient_detected():
    facts_meds = []
    active, _, warnings = medication_reconciler.reconcile([])
    # build two identities with same ingredient via engine duplication
    meds = [_ident("lisinopril", "29046", ["lisinopril"], "a"),
            _ident("lisinopril 20 mg", "29046", ["lisinopril"], "b")]
    conflicts = conflict_engine.evaluate(proposed_and_active=meds, signals=_CLEAN_SIGNALS)
    assert any(c.conflict_type == "therapeutic_duplication" for c in conflicts)


# ---- golden cases --------------------------------------------------------
def test_case2_label_contraindication_blocks(monkeypatch):
    meds = [_ident("spironolactone", "9997", ["spironolactone"])]
    conflicts = conflict_engine.evaluate(proposed_and_active=meds, signals=_RENAL_SIGNALS)
    assert any(c.severity == "blocked_for_draft" and c.authoritative_evidence for c in conflicts)


def test_case1_no_conflict_never_says_safe():
    meds = [_ident("dapagliflozin", "1488564", ["dapagliflozin"])]
    conflicts = conflict_engine.evaluate(proposed_and_active=meds, signals=_CLEAN_SIGNALS)
    hard = [c for c in conflicts if c.severity in ("blocked_for_draft", "high_concern")]
    assert not hard
    for c in conflicts:
        assert "safe medication" not in c.clinical_statement.lower()


def test_case6_allergy_conflict_blocks():
    meds = [_ident("sulfamethoxazole", None, ["sulfamethoxazole"])]
    sig = {**_CLEAN_SIGNALS, "allergen_terms": ["sulfamethoxazole"], "allergy_fact_ids": ["a1"]}
    conflicts = conflict_engine.evaluate(proposed_and_active=meds, signals=sig)
    assert any(c.conflict_type == "allergy_conflict" and c.severity == "blocked_for_draft" for c in conflicts)


def test_case7_missing_kidney_evidence_reported():
    meds = [_ident("spironolactone", "9997", ["spironolactone"])]
    conflicts = conflict_engine.evaluate(proposed_and_active=meds, signals=_RENAL_SIGNALS)
    assert any(c.conflict_type == "monitoring_gap" for c in conflicts)
    assert any("potassium" in m.lower() for c in conflicts for m in c.missing_information)


def test_conflict_requires_label_no_invented_interaction():
    # A med with no corpus label → insufficient_evidence, never a fabricated conflict.
    meds = [_ident("obscuramide", None, ["obscuramide"])]
    conflicts = conflict_engine.evaluate(proposed_and_active=meds, signals=_RENAL_SIGNALS)
    assert all(c.conflict_type in ("insufficient_evidence",) or c.authoritative_evidence or c.supplemental_evidence
               for c in conflicts)
    assert any(c.conflict_type == "insufficient_evidence" for c in conflicts)


def test_case8_same_class_alternative_excluded():
    target = _ident("spironolactone", "9997", ["spironolactone"])
    cites = [{"passage": "mineralocorticoid receptor antagonist and SGLT2 inhibitor", "title": "AHA",
              "version": "2022", "source_id": "aha", "publication_date": "2022-04-01"}]
    alts = alternative_engine.generate(target_med=target, signals=_RENAL_SIGNALS,
                                       guideline_citations=cites, indication="HFrEF")
    epl = [a for a in alts if "eplerenone" in a.medication_identity.original_text.lower()]
    assert epl and epl[0].display_status == "excluded_due_to_conflict"


def test_cross_class_lower_conflict_candidate_present():
    target = _ident("spironolactone", "9997", ["spironolactone"])
    cites = [{"passage": "combining ... an SGLT2 inhibitor", "title": "AHA", "version": "2022",
              "source_id": "aha", "publication_date": "2022-04-01"}]
    alts = alternative_engine.generate(target_med=target, signals=_RENAL_SIGNALS,
                                       guideline_citations=cites, indication="HFrEF")
    dapa = [a for a in alts if "dapagliflozin" in a.medication_identity.original_text.lower()]
    assert dapa and dapa[0].display_status == "candidate_for_clinician_review"
    assert dapa[0].guideline_evidence, "cross-class candidate must carry guideline evidence"


def test_case10_no_alternative_when_no_guideline():
    target = _ident("spironolactone", "9997", ["spironolactone"])
    alts = alternative_engine.generate(target_med=target, signals=_RENAL_SIGNALS,
                                       guideline_citations=[], indication="HFrEF")
    assert alternative_engine.displayable(alts) == []


# ---- report mentions -----------------------------------------------------
def test_report_mention_negation_and_family():
    ms = cme.extract("No evidence of pulmonary embolism. Family history of diabetes. Possible sleep apnea.")
    by = {m.normalized_display: m for m in ms}
    assert by["pulmonary embolism"].status == "negated_report_mention"
    assert by["diabetes mellitus"].status == "family_history"
    assert by["obstructive sleep apnea"].status in ("uncertain", "possible_report_mention")
    # negated + family never require confirmation as patient morbidity
    conf = {m.normalized_display for m in cme.requiring_confirmation(ms)}
    assert "pulmonary embolism" not in conf and "diabetes mellitus" not in conf


# ---- critic --------------------------------------------------------------
def test_critic_blocks_dose_and_banned_language():
    from python.hearttwin.careguard.medications.schemas import MedicationSafetyConflict
    bad = MedicationSafetyConflict(
        conflict_id="c", proposed_medication_id="m", conflict_type="drug_disease_interaction",
        severity="high_concern", headline="x",
        clinical_statement="This is the safest medication, take 25 mg daily.",
    )
    out = safety_critic.critique(conflicts=[bad], alternatives=[], report_mentions_confirmed_as_fact=False)
    assert out.safe_to_display is False
    assert any("dose" in r for r in out.blocked_reasons)
    assert any("banned" in r for r in out.blocked_reasons)


def test_critic_blocks_report_mention_treated_as_fact():
    out = safety_critic.critique(conflicts=[], alternatives=[], report_mentions_confirmed_as_fact=True)
    assert out.safe_to_display is False


# ---- source policy -------------------------------------------------------
def test_drugbank_refuses_without_license(monkeypatch):
    monkeypatch.setenv("DRUGBANK_ENABLED", "true")
    monkeypatch.setenv("DRUGBANK_LICENSE_CONFIRMED", "false")
    ok, reason = source_registry.drugbank_loadable()
    assert ok is False and "license" in reason.lower()


def test_kaggle_prohibited_as_authority():
    import pytest
    from python.hearttwin.careguard.errors import SafetyBoundaryError
    with pytest.raises(SafetyBoundaryError):
        source_registry.assert_not_prohibited("some_kaggle_medicine_dataset")


def test_source_status_reports_tiers():
    st = {s["source_id"]: s for s in source_registry.all_source_status()}
    assert st["dailymed"]["authority_tier"] == "A"
    assert st["ddinter"]["authority_tier"] == "B"
    assert st["drugbank"]["authority_tier"] == "C"
    assert st["drugbank"]["loadable"] is False


def test_sider_is_supplemental_only():
    from python.hearttwin.careguard.medications import evidence_policy
    assert evidence_policy.sider_can_block() is False
    assert evidence_policy.is_supplemental_only("sider") is True
