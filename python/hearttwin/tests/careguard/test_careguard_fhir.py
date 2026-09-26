"""FHIR ingestion + provenance tests (spec §9, §19)."""

from __future__ import annotations

import copy

import pytest

from python.hearttwin.careguard.errors import FhirValidationError
from python.hearttwin.careguard.fhir import bundle_validator, normalizer, parser


def test_valid_bundle_parsed_with_facts(load_fixture):
    bundle = load_fixture("cardiorenal-bundle.json")
    parsed = parser.parse_bundle(bundle)
    assert parsed.validation.valid is True
    assert parsed.validation.has_patient is True
    assert len(parsed.facts) > 0
    cats = {f.category for f in parsed.facts}
    assert {"condition", "medication", "observation", "allergy"} <= cats


def test_every_fact_has_provenance_pointer(load_fixture):
    parsed = parser.parse_bundle(load_fixture("cardiorenal-bundle.json"))
    for f in parsed.facts:
        assert f.json_pointer.startswith("/entry/"), f"{f.category} lacks a JSON pointer"
        assert f.source_bundle_id
        assert f.assertion_type == "recorded"


def test_units_and_codes_preserved(load_fixture):
    parsed = parser.parse_bundle(load_fixture("cardiorenal-bundle.json"))
    egfr = [f for f in parsed.facts if f.code == "48642-3"]
    assert egfr, "eGFR observation not extracted"
    assert egfr[0].value == 38
    assert "mL/min" in (egfr[0].unit or "")
    assert egfr[0].code_system == "loinc"
    rx = [f for f in parsed.facts if f.category == "medication" and f.code == "9997"]
    assert rx and rx[0].code_system == "rxnorm"  # spironolactone RxCUI preserved


def test_missing_potassium_detected(load_fixture):
    parsed = parser.parse_bundle(load_fixture("cardiorenal-bundle.json"))
    joined = " ".join(parsed.missing_critical_evidence).lower()
    assert "potassium" in joined, "missing-potassium not flagged despite K-affecting meds"


def test_malformed_bundle_rejected():
    with pytest.raises(FhirValidationError):
        parser.parse_bundle({"resourceType": "Patient", "id": "x"})
    with pytest.raises(FhirValidationError):
        parser.parse_bundle("not a bundle")


def test_duplicate_resource_ids_reported(load_fixture):
    bundle = load_fixture("cardiorenal-bundle.json")
    dup = copy.deepcopy(bundle)
    dup["entry"].append(copy.deepcopy(dup["entry"][2]))  # duplicate a Condition
    summary = bundle_validator.validate_bundle(dup)
    assert any("duplicate" in i for i in summary.issues)


def test_unresolved_reference_warned():
    bundle = {
        "resourceType": "Bundle",
        "id": "b1",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Condition", "id": "c1", "subject": {"reference": "Patient/ghost"}}}
        ],
    }
    summary = bundle_validator.validate_bundle(bundle)
    assert any("unresolved reference" in w for w in summary.warnings)


def test_unsupported_resource_recorded_not_dropped():
    bundle = {
        "resourceType": "Bundle",
        "id": "b2",
        "type": "collection",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p1"}},
            {"resource": {"resourceType": "NutritionOrder", "id": "n1"}},
        ],
    }
    parsed = parser.parse_bundle(bundle)
    assert any(u["resourceType"] == "NutritionOrder" for u in parsed.unsupported_resources)


def test_absent_condition_not_inferred(load_fixture):
    """Parser must not invent conditions that aren't in the Bundle."""
    parsed = parser.parse_bundle(load_fixture("cardiorenal-bundle.json"))
    condition_displays = {str(f.display or "").lower() for f in parsed.facts if f.category == "condition"}
    # Diabetes is NOT in the bundle — it must not appear.
    assert not any("diabetes" in d for d in condition_displays)


def test_medications_deduplicated(load_fixture):
    bundle = load_fixture("cardiorenal-bundle.json")
    dup = copy.deepcopy(bundle)
    dup["entry"].append(copy.deepcopy([e for e in dup["entry"] if e["resource"]["id"] == "med-spironolactone"][0]))
    parsed = parser.parse_bundle(dup)
    spiro = [f for f in parsed.facts if f.code == "9997"]
    assert len(spiro) == 1, "duplicate medication not deduped"


def test_patient_context_classifies_cardiac_vs_noncardiac(load_fixture):
    parsed = parser.parse_bundle(load_fixture("cardiorenal-bundle.json"))
    ctx = normalizer.build_patient_context("case-x", parsed)
    assert any("heart failure" in str(f.display).lower() for f in ctx.active_cardiac_problem)
    assert any("kidney" in str(f.display).lower() for f in ctx.active_non_cardiac_conditions)
    assert ctx.provenance_coverage == 1.0
    assert ctx.data_quality_score > 0.5
    assert ctx.medications and ctx.allergies
