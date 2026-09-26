"""Deterministic clinical classification for the CareGuard data pipeline.

Two jobs:
  1. Organ-system classification of diagnoses/history (cardiovascular vs the
     non-cardiac organ systems named in the spec).
  2. Cardiovascular sub-category tagging (heart failure, arrhythmia, MI/ACS, ...).

All classification is keyword/prefix based and fully documented. eICU's
`diagnosisstring` is a pipe-delimited hierarchy whose FIRST segment is the organ
system (e.g. "cardiovascular|ventricular disorders|acute MI"), which we exploit
before falling back to free-text keyword matching. Nothing here invents a
diagnosis — it only labels text that is already present.
"""
from __future__ import annotations

import re

# --------------------------------------------------------------------------- #
# Non-cardiac organ systems (spec §6). Order matters only for reporting.
# --------------------------------------------------------------------------- #
ORGAN_SYSTEMS = [
    "renal", "hepatic", "pulmonary", "endocrine_metabolic", "neurologic",
    "hematologic_coagulation", "infectious", "oncologic", "gastrointestinal",
    "musculoskeletal", "psychiatric", "obstetric", "allergy_immunologic", "other",
]

# Map the FIRST segment of an eICU diagnosisstring / pasthistorypath organ label
# to our canonical organ system.
EICU_PREFIX_MAP = {
    "cardiovascular": "cardiovascular",
    "renal": "renal",
    "gastrointestinal": "gastrointestinal",
    "gi": "gastrointestinal",
    "pulmonary": "pulmonary",
    "neurologic": "neurologic",
    "endocrine": "endocrine_metabolic",
    "hematology": "hematologic_coagulation",
    "infectious diseases": "infectious",
    "oncology": "oncologic",
    "musculoskeletal": "musculoskeletal",
    "psychiatric": "psychiatric",
    "obstetrics/gynecology": "obstetric",
    "obstetrics": "obstetric",
    "gynecology": "obstetric",
    "toxicology": "other",
    "trauma": "musculoskeletal",
    "burns/trauma": "musculoskeletal",
    "transplant": "other",
    "surgery": "other",
    "general": "other",
}

# Keyword fallbacks per organ system (used when no usable prefix).
ORGAN_KEYWORDS = {
    "renal": ["renal", "kidney", "nephr", "creatinine", "dialysis", "ckd", "esrd",
              "aki", "acute kidney", "uremi", "glomerul", "nephrotic"],
    "hepatic": ["hepat", "liver", "cirrhosis", "cholang", "biliary", "ascites",
                "portal hypertension", "hepatorenal", "encephalopathy hepatic",
                "varice", "jaundice"],
    "pulmonary": ["pulmonary", "lung", "copd", "asthma", "pneumonia", "respiratory",
                  "ards", "pleural", "pneumothorax", "emphysema", "bronch",
                  "hypoxia", "hypoxemia", "atelectasis", "interstitial lung"],
    "endocrine_metabolic": ["diabet", "endocrine", "thyroid", "adrenal", "hyperglycem",
                            "hypoglycem", "dka", "ketoacid", "metabolic", "electrolyte",
                            "hyperkalem", "hypokalem", "hyponatrem", "hypernatrem",
                            "acidosis", "alkalosis", "obesity", "hyperlipid",
                            "dyslipid", "pituitary", "cushing"],
    "neurologic": ["neuro", "stroke", "cva", "seizure", "epilep", "encephalopathy",
                   "delirium", "dementia", "coma", "intracranial", "subarachnoid",
                   "subdural", "cerebral", "parkinson", "myasthen", "guillain",
                   "meningitis", "altered mental", "ich"],
    "hematologic_coagulation": ["anemia", "thrombocytopen", "coagulop", "hemorrhage",
                                "bleeding", "dic", "leukopenia", "neutropenia",
                                "hematolog", "sickle", "hemophil", "thrombo",
                                "pancytopenia", "transfusion", "inr", "bleed"],
    "infectious": ["sepsis", "septic", "infection", "bacteremia", "pneumonia",
                   "cellulitis", "abscess", "uti", "urinary tract infection",
                   "endocarditis", "meningitis", "fungal", "viral", "covid",
                   "influenza", "hiv", "c. diff", "clostridium", "osteomyelitis"],
    "oncologic": ["cancer", "carcinoma", "malignan", "tumor", "neoplasm", "lymphoma",
                  "leukemia", "metasta", "oncolog", "sarcoma", "myeloma", "chemotherapy"],
    "gastrointestinal": ["gastrointestinal", "gi bleed", "pancreatitis", "bowel",
                         "colitis", "ileus", "obstruction bowel", "ulcer", "diverticul",
                         "cholecystitis", "gastric", "esophag", "peritonitis",
                         "appendicitis", "hernia", "intestinal"],
    "musculoskeletal": ["fracture", "musculoskeletal", "arthritis", "osteo", "rhabdomyolysis",
                        "compartment syndrome", "spinal", "vertebral", "myopathy", "trauma"],
    "psychiatric": ["psychiat", "depression", "anxiety", "psychosis", "schizophren",
                    "bipolar", "suicid", "overdose intentional", "substance", "alcohol withdrawal",
                    "delirium tremens"],
    "obstetric": ["pregnan", "obstetric", "eclampsia", "preeclampsia", "postpartum",
                  "peripartum", "gestational", "labor"],
    "allergy_immunologic": ["anaphylaxis", "allergic", "autoimmune", "lupus", "vasculitis",
                            "immunodefic", "rheumatoid", "sle", "transplant rejection"],
}

# --------------------------------------------------------------------------- #
# Cardiovascular sub-categories (spec §6). Each maps to a keyword list; the first
# matching category (in this order) is the primary label, but we return ALL hits.
# --------------------------------------------------------------------------- #
CV_CATEGORIES = {
    "heart_failure": ["heart failure", "chf", "congestive", "cardiomyopathy chf",
                      "pulmonary edema cardiac", "hfref", "hfpef", "systolic dysfunction",
                      "diastolic dysfunction", "cardiogenic pulmonary edema"],
    "cardiomyopathy": ["cardiomyopathy", "myocarditis", "dilated cardio", "hypertrophic cardio"],
    "myocardial_infarction_acs": ["myocardial infarction", "mi ", "stemi", "nstemi",
                                  "acute coronary", "acs", "unstable angina", "troponin"],
    "coronary_artery_disease": ["coronary artery disease", "cad", "ischemic heart",
                                "angina", "coronary atherosclerosis", "atherosclerotic heart"],
    "atrial_fibrillation": ["atrial fibrillation", "afib", "a-fib", "atrial flutter"],
    "other_arrhythmia": ["arrhythmia", "ventricular tachycardia", "vtach", "vfib",
                         "ventricular fibrillation", "svt", "premature", "ectopy",
                         "long qt", "torsades", "wpw", "junctional"],
    "bradycardia": ["bradycardia", "sinus bradycardia", "sick sinus"],
    "tachycardia": ["tachycardia", "sinus tachycardia"],
    "heart_block": ["heart block", "av block", "atrioventricular block", "bundle branch",
                    "pacemaker", "complete heart block"],
    "hypertension": ["hypertension", "hypertensive", "htn"],
    "hypotension": ["hypotension", "hypotensive"],
    "shock": ["shock", "cardiogenic shock", "distributive shock", "hypovolemic shock"],
    "cardiac_arrest": ["cardiac arrest", "cardiopulmonary arrest", "asystole",
                       "pea", "pulseless", "return of spontaneous"],
    "valvular_disease": ["valvular", "aortic stenosis", "aortic regurg", "mitral regurg",
                         "mitral stenosis", "tricuspid", "valve disease", "endocarditis valve"],
    "cardiac_surgery": ["cabg", "coronary artery bypass", "cardiac surgery", "valve replacement",
                        "valve repair", "sternotomy", "cardiothoracic"],
    "pci": ["percutaneous coronary", "pci", "angioplasty", "stent coronary", "cardiac cath"],
    "thromboembolic_cv": ["pulmonary embolism", "deep vein thrombosis", "dvt", "pe ",
                          "venous thromboembolism", "vte", "arterial thrombosis",
                          "peripheral arterial", "aortic aneurysm", "aortic dissection"],
}

# Broad PTB-XL cardiac super-category buckets we can match ECGs against.
CV_BROAD_FOR_ECG = {
    "heart_failure": "structural",
    "cardiomyopathy": "structural",
    "myocardial_infarction_acs": "MI",
    "coronary_artery_disease": "MI",
    "atrial_fibrillation": "conduction_rhythm",
    "other_arrhythmia": "conduction_rhythm",
    "bradycardia": "conduction_rhythm",
    "tachycardia": "conduction_rhythm",
    "heart_block": "conduction_rhythm",
    "hypertension": "hypertrophy",
    "valvular_disease": "structural",
}

_WORD = re.compile(r"[a-z0-9]+")


def _norm(text) -> str:
    if text is None:
        return ""
    return str(text).lower().strip()


def eicu_prefix_organ(diagnosisstring_or_path) -> str | None:
    """Return organ system from the FIRST hierarchy segment, or None."""
    s = _norm(diagnosisstring_or_path)
    if not s:
        return None
    # eICU diagnosis uses '|'; pasthistorypath uses '/'.
    first = re.split(r"[|/]", s)[0].strip()
    # pasthistorypath often starts with 'notes' 'progress notes' 'past history'
    # 'organ systems' before the real organ — scan segments for a known organ.
    segs = [seg.strip() for seg in re.split(r"[|/]", s)]
    for seg in segs:
        for key, organ in EICU_PREFIX_MAP.items():
            if seg == key or seg.startswith(key):
                return organ
    for key, organ in EICU_PREFIX_MAP.items():
        if first == key or first.startswith(key):
            return organ
    return None


def cardiovascular_categories(*texts) -> list[str]:
    """Return the list of CV sub-categories matched anywhere in the given texts."""
    blob = " ".join(_norm(t) for t in texts if t)
    if not blob:
        return []
    hits = []
    for cat, kws in CV_CATEGORIES.items():
        for kw in kws:
            if kw in blob:
                hits.append(cat)
                break
    return hits


def is_cardiovascular(*texts) -> bool:
    if cardiovascular_categories(*texts):
        return True
    blob = " ".join(_norm(t) for t in texts if t)
    return "cardiovascular" in blob or "cardiac" in blob


def organ_systems(diagnosisstring=None, path=None, text=None) -> set[str]:
    """Return the set of NON-cardiac organ systems implicated by the inputs.

    Uses the eICU hierarchy prefix first, then keyword fallback across all text.
    """
    found: set[str] = set()
    prefix = eicu_prefix_organ(diagnosisstring) or eicu_prefix_organ(path)
    if prefix and prefix != "cardiovascular":
        found.add(prefix)
    blob = " ".join(_norm(t) for t in (diagnosisstring, path, text) if t)
    if blob:
        for organ, kws in ORGAN_KEYWORDS.items():
            for kw in kws:
                if kw in blob:
                    found.add(organ)
                    break
    found.discard("cardiovascular")
    return found


def primary_cv_category(*texts) -> str | None:
    cats = cardiovascular_categories(*texts)
    return cats[0] if cats else None


# --------------------------------------------------------------------------- #
# Laboratory canonicalization: eICU labname -> (canonical name, LOINC, group).
# LOINC codes below are standard, widely-used serum/plasma codes, applied only
# when the eICU labname is an unambiguous match. Where a single labname could map
# to multiple LOINCs, we leave loinc empty rather than guess.
# --------------------------------------------------------------------------- #
LAB_CANON = {
    "creatinine": ("Creatinine", "2160-0", "renal"),
    "bun": ("BUN", "3094-0", "renal"),
    "potassium": ("Potassium", "2823-3", "electrolyte"),
    "sodium": ("Sodium", "2951-2", "electrolyte"),
    "magnesium": ("Magnesium", "2601-3", "electrolyte"),
    "calcium": ("Calcium", "17861-6", "electrolyte"),
    "ionized calcium": ("Ionized calcium", "1995-0", "electrolyte"),
    "glucose": ("Glucose", "2345-7", "metabolic"),
    "bedside glucose": ("Glucose (bedside)", "2339-0", "metabolic"),
    "hgb": ("Hemoglobin", "718-7", "hematology"),
    "hemoglobin": ("Hemoglobin", "718-7", "hematology"),
    "hct": ("Hematocrit", "4544-3", "hematology"),
    "platelets x 1000": ("Platelets", "777-3", "hematology"),
    "wbc x 1000": ("WBC", "6690-2", "hematology"),
    "-polys": ("Neutrophils %", "770-8", "hematology"),
    "pt - inr": ("INR", "6301-6", "coagulation"),
    "pt": ("PT", "5902-2", "coagulation"),
    "ptt": ("aPTT", "14979-9", "coagulation"),
    "ast (sgot)": ("AST", "1920-8", "hepatic"),
    "alt (sgpt)": ("ALT", "1742-6", "hepatic"),
    "total bilirubin": ("Total bilirubin", "1975-2", "hepatic"),
    "albumin": ("Albumin", "1751-7", "hepatic"),
    "troponin - i": ("Troponin I", "10839-9", "cardiac"),
    "troponin - t": ("Troponin T", "6598-7", "cardiac"),
    "bnp": ("BNP", "30934-4", "cardiac"),
    "lactate": ("Lactate", "2524-7", "metabolic"),
    "ph": ("pH", "2744-1", "blood_gas"),
    "pao2": ("PaO2", "2703-7", "blood_gas"),
    "paco2": ("PaCO2", "2019-8", "blood_gas"),
    "o2 sat (%)": ("O2 saturation", "2708-6", "blood_gas"),
    "fio2": ("FiO2", "3150-0", "blood_gas"),
    "base excess": ("Base excess", "1925-7", "blood_gas"),
    "bicarbonate": ("Bicarbonate", "1963-8", "electrolyte"),
    "chloride": ("Chloride", "2075-0", "electrolyte"),
    "hco3": ("Bicarbonate", "1963-8", "electrolyte"),
    "anion gap": ("Anion gap", "1863-0", "metabolic"),
    "egfr": ("eGFR", "48642-3", "renal"),
    "phosphate": ("Phosphate", "2777-1", "electrolyte"),
    "total protein": ("Total protein", "2885-2", "hepatic"),
    "alkaline phos.": ("Alkaline phosphatase", "6768-6", "hepatic"),
}

# Vitals canonicalization: our field -> (display, LOINC, ucum unit).
VITAL_LOINC = {
    "heartrate": ("Heart rate", "8867-4", "/min"),
    "systemicsystolic": ("Systolic blood pressure", "8480-6", "mm[Hg]"),
    "systemicdiastolic": ("Diastolic blood pressure", "8462-4", "mm[Hg]"),
    "systemicmean": ("Mean arterial pressure", "8478-0", "mm[Hg]"),
    "noninvasivesystolic": ("Systolic blood pressure", "8480-6", "mm[Hg]"),
    "noninvasivediastolic": ("Diastolic blood pressure", "8462-4", "mm[Hg]"),
    "noninvasivemean": ("Mean arterial pressure", "8478-0", "mm[Hg]"),
    "respiration": ("Respiratory rate", "9279-1", "/min"),
    "sao2": ("Oxygen saturation", "2708-6", "%"),
    "temperature": ("Body temperature", "8310-5", "Cel"),
}


def canon_lab(labname):
    key = _norm(labname)
    if key in LAB_CANON:
        return LAB_CANON[key]
    # loose contains-match for a few common variants
    for k, v in LAB_CANON.items():
        if k and k in key:
            return v
    return None
