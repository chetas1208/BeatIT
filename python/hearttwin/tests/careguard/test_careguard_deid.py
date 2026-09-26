"""Deidentification + redaction guarantees (spec §7 retention boundary)."""

from __future__ import annotations

from python.hearttwin.careguard.security import (
    assert_no_identifiers,
    deidentify_for_model,
    opaque_id,
    redact_text,
)


def _identifiable_payload() -> dict:
    return {
        "resourceType": "Patient",
        "name": [{"family": "Rivera", "given": ["Maria"]}],
        "birthDate": "1957-03-14",
        "telecom": [{"system": "phone", "value": "415-555-0199"}],
        "address": [{"line": ["123 Main St"], "city": "Oakland"}],
        "identifier": [{"value": "MRN-99887766"}],
        "condition": {
            "code": "I50.9",
            "code_system": "icd10",
            "display": "Heart failure",
            "status": "active",
            "effective_at": "2026-02-01",
        },
        "observation": {"code": "2160-0", "value": 2.4, "unit": "mg/dL"},
    }


def test_deidentify_drops_all_identifier_keys():
    clean = deidentify_for_model(_identifiable_payload())
    leaked = assert_no_identifiers(clean)
    assert leaked == [], f"identifiers survived deidentification: {leaked}"


def test_deidentify_preserves_clinical_facts():
    clean = deidentify_for_model(_identifiable_payload())
    assert clean["condition"]["code"] == "I50.9"
    assert clean["condition"]["display"] == "Heart failure"
    assert clean["observation"]["value"] == 2.4
    assert clean["observation"]["unit"] == "mg/dL"


def test_deidentify_converts_dates_to_relative_marker():
    clean = deidentify_for_model({"note": "seen on 2026-02-01 for followup"})
    assert "2026-02-01" not in clean["note"]
    assert "relative-clinical-interval" in clean["note"]


def test_redact_text_masks_phi_patterns():
    red = redact_text("SSN 123-45-6789 email a@b.com phone 415-555-0199 id 998877665544")
    assert "123-45-6789" not in red
    assert "a@b.com" not in red
    assert "415-555-0199" not in red
    assert "998877665544" not in red


def test_opaque_id_is_stable_and_nonidentifying():
    a = opaque_id("case-1", "Patient", "p1")
    b = opaque_id("case-1", "Patient", "p1")
    assert a == b
    assert a.startswith("cg-")
    assert "p1" not in a
