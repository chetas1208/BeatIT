"""End-to-end staged pipeline via the real flag-on app (spec §20)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _drive(client, base):
    cid = client.post(base + "/fhir/import",
                      json={"fixture_id": "cardiorenal-bundle",
                            "clinical_question": "HFrEF review with CKD stage 3b"}).json()["case_id"]
    rid = client.post(base + "/runs", json={"case_id": cid, "workflow_intent": "care_plan_comparison"}).json()["run"]["run_id"]
    stages = []
    for _ in range(12):
        out = client.post(base + f"/runs/{rid}/next").json()
        if out.get("stage_result"):
            stages.append(out["stage_result"])
        if out.get("terminal"):
            break
    return cid, rid, stages, out


def test_full_flow_runs_all_stages(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    client = TestClient(app)
    base = "/api/v1/careguard"
    cid, rid, stages, final = _drive(client, base)

    stage_ids = [s["stage_id"] for s in stages]
    assert "encounter_intake" in stage_ids
    assert "clinical_critic" in stage_ids
    assert final["run"]["status"] == "completed"
    # every stage did real work (non-empty structured output)
    for s in stages:
        assert s["structured_output"], f"{s['stage_id']} produced empty output"


def test_candidates_are_plural_and_have_no_dose(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    client = TestClient(app)
    base = "/api/v1/careguard"
    cid, _, _, _ = _drive(client, base)
    cands = client.get(base + f"/cases/{cid}/candidates").json()["candidates"]
    assert len(cands) >= 2, "candidate options must be plural"
    import re
    dose = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|g|units?)\b", re.IGNORECASE)
    for c in cands:
        assert c["clinician_review_required"] is True
        blob = c["description"] + " ".join(c["reasons_for"] + c["reasons_against"])
        assert not dose.search(blob), f"candidate {c['candidate_id']} contains a dose"


def test_evidence_and_provenance_present(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    client = TestClient(app)
    base = "/api/v1/careguard"
    cid, _, _, _ = _drive(client, base)
    cites = client.get(base + f"/cases/{cid}/evidence").json()["citations"]
    assert cites, "guideline citations missing"
    for c in cites:
        assert c["passage"] and c["sha256"] and c["canonical_source"]
    ctx = client.get(base + f"/cases/{cid}/context").json()["patient_context"]
    for f in ctx["active_cardiac_problem"]:
        assert f["json_pointer"].startswith("/entry/")


def test_simulation_ran_and_preserved_baseline(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    client = TestClient(app)
    base = "/api/v1/careguard"
    cid, _, _, _ = _drive(client, base)
    sim = client.get(base + f"/cases/{cid}/simulation").json()["simulation"]
    assert sim["ok"] is True
    assert sim["baseline_inputs_unchanged"] is True
    assert sim["reused_functions"], "must record which DualBeat functions were reused"
    assert "Simulated physiologic scenario" in sim["label"]


def test_critic_scored_and_audit_recorded(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    client = TestClient(app)
    base = "/api/v1/careguard"
    cid, _, _, _ = _drive(client, base)
    critic = client.get(base + f"/cases/{cid}/critic").json()["critic"]
    assert "overall_safety" in critic["scorecard"]
    audit = client.get(base + f"/cases/{cid}/audit").json()
    assert audit["count"] > 0
    # existing DualBeat route still works after CareGuard flow
    assert client.get("/api/v1/health").status_code == 200


def test_idempotent_next_does_not_duplicate_stage(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    client = TestClient(app)
    base = "/api/v1/careguard"
    cid = client.post(base + "/fhir/import", json={"fixture_id": "cardiorenal-bundle"}).json()["case_id"]
    rid = client.post(base + "/runs", json={"case_id": cid}).json()["run"]["run_id"]
    first = client.post(base + f"/runs/{rid}/next").json()
    run_after = client.get(base + f"/runs/{rid}").json()["run"]
    assert run_after["completed_stages"].count("encounter_intake") == 1


def test_feedback_override_requires_reason(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    client = TestClient(app)
    base = "/api/v1/careguard"
    cid = client.post(base + "/fhir/import", json={"fixture_id": "cardiorenal-bundle"}).json()["case_id"]
    r = client.post(base + f"/cases/{cid}/feedback", json={"decision": "override", "reason": ""})
    assert r.status_code == 422
    ok = client.post(base + f"/cases/{cid}/feedback", json={"decision": "override", "reason": "clinician accepts risk"})
    assert ok.status_code == 200
