"""Deterministic eICU-assembled-record -> FHIR R4 Bundle builder.

Produces exactly the Bundle shape the HeartTwin CareGuard ingestion pipeline
consumes (Patient + Encounter + Condition + Observation + Medication* +
AllergyIntolerance + Procedure + CarePlan/Goal + DiagnosticReport for the ECG).

Rules honoured:
  * Never invent SNOMED/LOINC/RxNorm codes, diagnosis dates, or doses. Codes are
    emitted only when present in the source (ICD-9/10 from eICU, LOINC from the
    documented lab/vital map, RxNorm from stage-07 normalization). Otherwise
    {"coding": [], "text": <original>}.
  * No PHI: Patient carries gender + an age-band extension only — no name,
    address, telecom, or identifier.
  * Every clinical resource carries a careguard provenance extension.
  * The ECG is represented as an external DiagnosticReport that explicitly states
    same_patient_as_ehr = false.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

PROV_URL = "https://hearttwin.local/careguard/provenance"
AGEBAND_URL = "https://hearttwin.local/careguard/age-band"
ECG_EXT_URL = "https://hearttwin.local/careguard/ecg-external"
SS = C.CODE_SYSTEMS
ICD9_SYSTEM = "http://hl7.org/fhir/sid/icd-9-cm"

_ICD10 = re.compile(r"^[A-TV-Z]\d")

# Bundle-size caps. eICU ICU stays can carry hundreds of repeated administration
# rows; the FHIR bundle keeps a deduped, representative set (all cardiovascular
# conditions are always retained). Full-fidelity rows remain in the per-case EHR
# CSVs. Counts of dropped items are recorded in the case quality report.
MAX_CONDITIONS = 80
MAX_MEDS = 80
MAX_ALLERGIES = 40


def _dedupe(items, keyfn):
    seen, out = set(), []
    for it in items:
        k = keyfn(it)
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def _prov_ext(*, source_table, source_row_id, source_column,
              assertion_type="recorded", confidence=1.0,
              mapping_rule_version="careguard-data.v1"):
    return {
        "url": PROV_URL,
        "extension": [
            {"url": "source_dataset", "valueString": "eICU-CRD Demo 2.0.1"},
            {"url": "source_table", "valueString": str(source_table)},
            {"url": "source_row_id", "valueString": str(source_row_id)},
            {"url": "source_column", "valueString": str(source_column)},
            {"url": "assertion_type", "valueString": assertion_type},
            {"url": "confidence", "valueDecimal": round(float(confidence), 3)},
            {"url": "mapping_rule_version", "valueString": mapping_rule_version},
            {"url": "conversion_timestamp", "valueString": C.now_iso()},
        ],
    }


def _split_icd(icd_raw):
    """Return (icd10_codes, icd9_codes) parsed from an eICU icd9code field."""
    icd10, icd9 = [], []
    if not icd_raw:
        return icd10, icd9
    for tok in re.split(r"[,;]", str(icd_raw)):
        t = tok.strip()
        if not t or t.lower() == "nan":
            continue
        (icd10 if _ICD10.match(t) else icd9).append(t)
    return icd10, icd9


def _clinical_status(status):
    code = "active" if status != "historical" else "inactive"
    return {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": code}]}


class Builder:
    def __init__(self, assembled, normalized_meds, ecg_assignment, cfg, echo_assignment=None):
        self.a = assembled
        self.meds = normalized_meds or {}
        self.ecg = ecg_assignment or {}
        self.echo = echo_assignment or {}
        self.cfg = cfg
        self.entries = []
        self.n = 0
        self.dropped_conditions = 0
        self.dropped_meds = 0

    def _pid(self):
        return f"patient-{self.a['patientunitstayid']}"

    def _add(self, resource):
        rid = resource["id"]
        self.entries.append({"fullUrl": f"urn:uuid:{rid}", "resource": resource})

    def _nid(self, prefix):
        self.n += 1
        return f"{prefix}-{self.a['patientunitstayid']}-{self.n}"

    # -- resources -------------------------------------------------------- #
    def patient(self):
        d = self.a["demographics"]
        res = {
            "resourceType": "Patient", "id": self._pid(),
            "gender": d.get("gender") or "unknown",
            "extension": [{"url": AGEBAND_URL, "valueString": d.get("age_band", "unknown")}],
        }
        self._add(res)

    def encounter(self):
        d = self.a["demographics"]
        res = {
            "resourceType": "Encounter", "id": self._nid("enc"), "status": "finished",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                      "code": "IMP", "display": "inpatient encounter"},
            "type": [{"text": f"ICU stay — {d.get('unit_type') or 'ICU'}"}],
            "subject": {"reference": f"Patient/{self._pid()}"},
            "reasonCode": [{"text": d.get("apache_admission_dx") or "ICU admission"}],
            "extension": [_prov_ext(source_table="patient",
                                    source_row_id=self.a["patientunitstayid"],
                                    source_column="unittype/apacheadmissiondx")],
        }
        self._add(res)

    def _select_conditions(self):
        """Dedupe diagnoses by text; keep ALL cardiovascular, then fill up to
        MAX_CONDITIONS with the rest (active first). Records how many dropped."""
        dx_only = [d for d in self.a["diagnoses"] if d["source_table"] != "treatment"]
        deduped = _dedupe(dx_only, lambda d: d["text"].lower())
        cv = [d for d in deduped if d.get("is_cardiovascular") or d.get("cv_categories")]
        rest = [d for d in deduped if d not in cv]
        rest.sort(key=lambda d: (d.get("clinical_status") != "active", d["text"]))
        keep = cv + rest[:max(0, MAX_CONDITIONS - len(cv))]
        self.dropped_conditions = len(deduped) - len(keep)
        return keep

    def conditions(self):
        for dx in self._select_conditions():
            icd10, icd9 = _split_icd(dx.get("icd_code"))
            coding = []
            for c in icd10:
                coding.append({"system": SS["icd10"], "code": c, "display": dx["text"][:120]})
            for c in icd9:
                coding.append({"system": ICD9_SYSTEM, "code": c, "display": dx["text"][:120]})
            res = {
                "resourceType": "Condition", "id": self._nid("cond"),
                "clinicalStatus": _clinical_status(dx.get("clinical_status")),
                "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category",
                                          "code": "problem-list-item"}]}],
                "code": {"coding": coding, "text": dx["text"]},
                "subject": {"reference": f"Patient/{self._pid()}"},
                "extension": [_prov_ext(source_table=dx["source_table"],
                                        source_row_id=dx["source_row_id"],
                                        source_column="diagnosisstring/pasthistoryvalue")],
            }
            self._add(res)

    def _obs(self, code_system, code, display, value, unit, ucum, *, table, row_id,
             assertion="recorded", category="laboratory"):
        coding = []
        if code:
            coding.append({"system": code_system, "code": code, "display": display})
        res = {
            "resourceType": "Observation", "id": self._nid("obs"), "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                      "code": category}]}],
            "code": {"coding": coding, "text": display},
            "subject": {"reference": f"Patient/{self._pid()}"},
            "extension": [_prov_ext(source_table=table, source_row_id=row_id,
                                    source_column="labresult/vital",
                                    assertion_type=assertion,
                                    confidence=1.0 if assertion == "recorded" else 0.95)],
        }
        if value is not None:
            res["valueQuantity"] = {"value": value, "unit": unit,
                                    "system": SS["ucum"], "code": ucum}
        self._add(res)

    def labs(self):
        # de-dup: keep the most recent (max offset) value per canonical lab
        best = {}
        for l in self.a["labs"]:
            if l.get("value") is None:
                continue
            key = l["canonical"]
            off = l.get("offset") or 0
            if key not in best or (off or 0) >= (best[key].get("offset") or 0):
                best[key] = l
        for l in best.values():
            self._obs(SS["loinc"], l["loinc"], l["canonical"], l["value"],
                      l.get("unit") or "", l.get("unit") or "", table="lab",
                      row_id=l["source_row_id"], category="laboratory")

    def vitals(self):
        import classify as X
        summary = self.a["vitals"].get("summary", {})
        # BP as a component observation if both present
        sys_v = summary.get("Systolic blood pressure")
        dia_v = summary.get("Diastolic blood pressure")
        if sys_v and dia_v:
            res = {
                "resourceType": "Observation", "id": self._nid("obs"), "status": "final",
                "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                          "code": "vital-signs"}]}],
                "code": {"coding": [{"system": SS["loinc"], "code": "85354-9",
                                     "display": "Blood pressure panel"}]},
                "subject": {"reference": f"Patient/{self._pid()}"},
                "component": [
                    {"code": {"coding": [{"system": SS["loinc"], "code": "8480-6",
                                          "display": "Systolic blood pressure"}]},
                     "valueQuantity": {"value": sys_v["mean"], "unit": "mmHg",
                                       "system": SS["ucum"], "code": "mm[Hg]"}},
                    {"code": {"coding": [{"system": SS["loinc"], "code": "8462-4",
                                          "display": "Diastolic blood pressure"}]},
                     "valueQuantity": {"value": dia_v["mean"], "unit": "mmHg",
                                       "system": SS["ucum"], "code": "mm[Hg]"}},
                ],
                "extension": [_prov_ext(source_table="vitalPeriodic/vitalAperiodic",
                                        source_row_id=self.a["patientunitstayid"],
                                        source_column="systolic/diastolic (mean of series)",
                                        assertion_type="derived_deterministically",
                                        confidence=0.95)],
            }
            self._add(res)
        # other single-value vitals (mean of series)
        singles = {"Heart rate": ("8867-4", "/min"), "Respiratory rate": ("9279-1", "/min"),
                   "Oxygen saturation": ("2708-6", "%"), "Body temperature": ("8310-5", "Cel"),
                   "Mean arterial pressure": ("8478-0", "mm[Hg]")}
        for name, (loinc, ucum) in singles.items():
            s = summary.get(name)
            if not s:
                continue
            self._obs(SS["loinc"], loinc, name, s["mean"], s.get("unit") or ucum, ucum,
                      table="vitalPeriodic/vitalAperiodic",
                      row_id=self.a["patientunitstayid"],
                      assertion="derived_deterministically", category="vital-signs")

    def medications(self):
        meds = _dedupe(self.a["medications"], lambda m: (m.get("text") or "").lower())
        self.dropped_meds = len(self.a["medications"]) - len(meds)
        for m in meds[:MAX_MEDS]:
            norm = self.meds.get((m.get("text") or "").lower(), {})
            coding = []
            if norm.get("rxcui"):
                coding.append({"system": SS["rxnorm"], "code": str(norm["rxcui"]),
                               "display": norm.get("normalized_name") or m["text"]})
            res = {
                "resourceType": "MedicationStatement", "id": self._nid("med"),
                "status": "active" if m.get("status") in ("active", "admission", "infusion") else "stopped",
                "medicationCodeableConcept": {"coding": coding, "text": m["text"]},
                "subject": {"reference": f"Patient/{self._pid()}"},
                "extension": [_prov_ext(source_table=m["source_table"],
                                        source_row_id=m["source_row_id"],
                                        source_column="drugname",
                                        confidence=norm.get("confidence", 0.0) or 0.0,
                                        assertion_type="recorded")],
            }
            if m.get("dosage"):
                res["dosage"] = [{"text": str(m["dosage"]) +
                                  (f" {m['route']}" if m.get("route") else "")}]
            self._add(res)

    def allergies(self):
        als = _dedupe(self.a["allergies"], lambda a: (a.get("name") or "").lower())[:MAX_ALLERGIES]
        for al in als:
            res = {
                "resourceType": "AllergyIntolerance", "id": self._nid("allergy"),
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                                               "code": "active"}]},
                "code": {"coding": [], "text": al["name"]},
                "patient": {"reference": f"Patient/{self._pid()}"},
                "extension": [_prov_ext(source_table="allergy", source_row_id=al["source_row_id"],
                                        source_column="allergyname")],
            }
            if al.get("type"):
                res["category"] = ["medication" if "drug" in str(al["type"]).lower() else "environment"]
            self._add(res)

    def procedures(self):
        tx = [d for d in self.a["diagnoses"] if d["source_table"] == "treatment"]
        tx = _dedupe(tx, lambda d: d["text"].lower())[:MAX_CONDITIONS]
        for dx in tx:
            res = {
                "resourceType": "Procedure", "id": self._nid("proc"), "status": "completed",
                "code": {"coding": [], "text": dx["text"]},
                "subject": {"reference": f"Patient/{self._pid()}"},
                "extension": [_prov_ext(source_table="treatment", source_row_id=dx["source_row_id"],
                                        source_column="treatmentstring")],
            }
            self._add(res)

    def careplan(self):
        goals = [c for c in self.a.get("careplan", []) if c.get("type") == "goal"]
        items = [c for c in self.a.get("careplan", []) if c.get("type") != "goal"]
        goal_refs = []
        for g in goals[:20]:
            gid = self._nid("goal")
            self._add({"resourceType": "Goal", "id": gid, "lifecycleStatus": "active",
                       "description": {"text": str(g.get("value") or g.get("group") or "care goal")},
                       "subject": {"reference": f"Patient/{self._pid()}"},
                       "extension": [_prov_ext(source_table="carePlanGoal",
                                               source_row_id=g.get("source_row_id"),
                                               source_column="cplgoalvalue")]})
            goal_refs.append({"reference": f"Goal/{gid}"})
        if items or goal_refs:
            activities = [{"detail": {"kind": "ServiceRequest", "status": "unknown",
                                      "description": str(it.get("value") or it.get("group"))[:200]}}
                          for it in items[:20] if (it.get("value") or it.get("group"))]
            res = {"resourceType": "CarePlan", "id": self._nid("careplan"), "status": "active",
                   "intent": "plan", "subject": {"reference": f"Patient/{self._pid()}"},
                   "extension": [_prov_ext(source_table="carePlanGeneral",
                                           source_row_id=self.a["patientunitstayid"],
                                           source_column="cplitemvalue")]}
            if goal_refs:
                res["goal"] = goal_refs
            if activities:
                res["activity"] = activities
            self._add(res)

    def ecg_report(self):
        if not self.ecg.get("assigned"):
            return
        res = {
            "resourceType": "DiagnosticReport", "id": self._nid("ecg"), "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                                      "code": "CUS", "display": "Cardiology"}]}],
            "code": {"coding": [{"system": SS["loinc"], "code": "11524-6", "display": "EKG study"}],
                     "text": "12-lead ECG (external matched modality, PTB-XL)"},
            "subject": {"reference": f"Patient/{self._pid()}"},
            "conclusion": f"PTB-XL superclass: {self.ecg.get('ecg_primary_superclass')}; "
                          f"rhythm: {self.ecg.get('ecg_rhythm') or 'n/a'}. "
                          + self.cfg["disclaimers"]["ecg_donor"],
            "extension": [{
                "url": ECG_EXT_URL,
                "extension": [
                    {"url": "ecg_source", "valueString": "PTB-XL"},
                    {"url": "ecg_record_id", "valueString": str(self.ecg.get("ecg_record_id"))},
                    {"url": "linkage_type", "valueString": "matched_external_modality"},
                    {"url": "same_patient_as_ehr", "valueBoolean": False},
                    {"url": "match_features", "valueString": self.ecg.get("match_features", "")},
                    {"url": "warning", "valueString": self.ecg.get("warning", "")},
                ],
            }],
        }
        self._add(res)

    def echo_report(self):
        if not self.echo.get("assigned"):
            return
        res = {
            "resourceType": "DiagnosticReport", "id": self._nid("echo"), "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                                      "code": "US", "display": "Ultrasound"}]}],
            "code": {"coding": [], "text": "Transthoracic echocardiogram — apical 4-chamber "
                     "(external matched modality, EchoNet-Dynamic)"},
            "subject": {"reference": f"Patient/{self._pid()}"},
            "conclusion": (f"Donor ejection fraction {self.echo.get('donor_ef')}% "
                           f"(EDV {self.echo.get('donor_edv')} mL, ESV {self.echo.get('donor_esv')} mL) "
                           "from EchoNet-Dynamic. These are the ECHO DONOR's measurements, NOT the "
                           "eICU patient's. " + self.echo.get("warning", "")),
            "extension": [{
                "url": "https://hearttwin.local/careguard/echo-external",
                "extension": [
                    {"url": "echo_source", "valueString": "EchoNet-Dynamic"},
                    {"url": "echo_record_id", "valueString": str(self.echo.get("echo_id"))},
                    {"url": "modality", "valueString": "US"},
                    {"url": "linkage_type", "valueString": "matched_external_modality"},
                    {"url": "same_patient_as_ehr", "valueBoolean": False},
                    {"url": "donor_ejection_fraction_pct", "valueString": str(self.echo.get("donor_ef"))},
                    {"url": "warning", "valueString": self.echo.get("warning", "")},
                ],
            }],
        }
        self._add(res)

    def build(self):
        d = self.a["demographics"]
        real = self.a.get("real_patient_data", True)
        tags = [
            {"system": C.CAREGUARD_TAG_SYSTEM,
             "code": "real-ehr-eicu" if real else "synthetic",
             "display": ("Real deidentified eICU ICU record (structured EHR)" if real
                         else "Synthetic, non-PHI record")},
            {"system": C.CAREGUARD_TAG_SYSTEM, "code": "research-only",
             "display": self.cfg["disclaimers"]["research_only"]},
            {"system": C.CAREGUARD_TAG_SYSTEM, "code": "composite-modalities",
             "display": self.cfg["disclaimers"]["composite"]},
        ]
        self.patient()
        self.encounter()
        self.conditions()
        self.labs()
        self.vitals()
        self.medications()
        self.allergies()
        self.procedures()
        self.careplan()
        self.ecg_report()
        self.echo_report()
        bundle = {
            "resourceType": "Bundle",
            "id": f"careguard-eicu-{self.a['patientunitstayid']}",
            "type": "collection",
            "meta": {"tag": tags},
            "entry": self.entries,
        }
        return bundle


def build_bundle(assembled, normalized_meds, ecg_assignment, cfg):
    return Builder(assembled, normalized_meds, ecg_assignment, cfg).build()


SUPPORTED = {
    "Patient", "Encounter", "Condition", "Observation", "DiagnosticReport",
    "MedicationRequest", "MedicationStatement", "AllergyIntolerance", "Procedure",
    "ImagingStudy", "ServiceRequest", "CarePlan", "Goal", "DocumentReference",
    "Practitioner", "Organization",
}


def _collect_refs(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "reference" and isinstance(v, str):
                out.append(v)
            else:
                _collect_refs(v, out)
    elif isinstance(node, list):
        for x in node:
            _collect_refs(x, out)


def validate_bundle_struct(bundle: dict) -> tuple[bool, list[str]]:
    """Structural FHIR R4 validation matching the CareGuard ingestion contract:
    Bundle type, entry list, per-resource resourceType/id, unique ids, resolvable
    internal references, exactly one Patient, provenance tags present."""
    issues = []
    if bundle.get("resourceType") != "Bundle":
        return False, ["resourceType != Bundle"]
    if not isinstance(bundle.get("id"), str) or not bundle["id"]:
        issues.append("missing Bundle.id")
    entries = bundle.get("entry")
    if not isinstance(entries, list) or not entries:
        return False, issues + ["entry missing/empty"]
    ids, types = set(), []
    for i, e in enumerate(entries):
        r = e.get("resource")
        if not isinstance(r, dict):
            issues.append(f"entry[{i}] has no resource"); continue
        rt = r.get("resourceType")
        if rt not in SUPPORTED:
            issues.append(f"entry[{i}] unsupported resourceType {rt}")
        rid = r.get("id")
        if not rid:
            issues.append(f"entry[{i}] missing resource id")
        elif rid in ids:
            issues.append(f"duplicate resource id {rid}")
        else:
            ids.add(rid)
        types.append(rt)
    if types.count("Patient") != 1:
        issues.append(f"expected exactly 1 Patient, found {types.count('Patient')}")
    refs = []
    _collect_refs(bundle, refs)
    for ref in refs:
        if "/" in ref:
            _, _, rid = ref.partition("/")
            if rid not in ids:
                issues.append(f"unresolved reference {ref}")
    tags = (bundle.get("meta") or {}).get("tag") or []
    if not any(t.get("system") == "https://hearttwin.local/careguard" for t in tags):
        issues.append("missing careguard provenance tag")
    return (len([x for x in issues if "unsupported" not in x]) == 0), issues
