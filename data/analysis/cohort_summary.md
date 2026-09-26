# HeartTwin CareGuard — Cohort Summary

_Generated 2026-07-18T23:36:28+00:00_

- Total packaged cases: **1000**
- Real eICU cases: **1000**  |  Synthetic fallback: **0**
- Cases with external ECG: **1000**  |  without: **0**
- Tiers: {'A': 1000}
- Sex: {'male': 600, 'female': 399}

## Cardiovascular
- {'heart_failure': 255, 'arrhythmia': 528, 'mi_acs': 285, 'hypertension': 696, 'cardiac_arrest': 76, 'cardiomyopathy': 36, 'cardiac_surgery': 153, 'by_category': {'heart_failure': 255, 'cardiomyopathy': 36, 'myocardial_infarction_acs': 285, 'coronary_artery_disease': 79, 'atrial_fibrillation': 201, 'other_arrhythmia': 327, 'bradycardia': 20, 'tachycardia': 43, 'heart_block': 76, 'hypertension': 696, 'hypotension': 236, 'shock': 336, 'cardiac_arrest': 76, 'valvular_disease': 63, 'cardiac_surgery': 153, 'pci': 14, 'thromboembolic_cv': 393}}

## Multimorbidity
- Mean non-cardiac organ systems: 5.458
- Median: 5.0
- Cardiovascular co-occurrence: {'cardiovascular+renal': 560, 'cardiovascular+hepatic': 104, 'cardiovascular+pulmonary': 803, 'cardiovascular+endocrine_metabolic': 652, 'cardiovascular+neurologic': 608, 'cardiovascular+hematologic_coagulation': 878, 'cardiovascular+infectious': 516, 'cardiovascular+oncologic': 209, 'cardiovascular+gastrointestinal': 564, 'cardiovascular+musculoskeletal': 150, 'cardiovascular+psychiatric': 63, 'cardiovascular+obstetric': 4, 'cardiovascular+allergy_immunologic': 45, 'cardiovascular+other': 302}

## Medications
- {'mean_medications_per_case': 60.83, 'median_medications_per_case': 31.5, 'unique_normalized_strings': 2135, 'normalization_rate': 0.9934, 'unresolved_strings': 14, 'cases_with_allergy_data': 481, 'label_evidence_unique': 973, 'cases_with_possible_therapeutic_duplication': 408}

## Laboratory availability
- {'Creatinine': 992, 'Potassium': 993, 'Sodium': 992, 'AST': 814, 'ALT': 813, 'INR': 679, 'Troponin I': 454, 'Troponin T': 82, 'BNP': 191, 'Lactate': 429}

## ECG (external matched modality)
- {'selected_records': 1000, 'superclass_distribution': {'HYP': 381, 'CD': 255, 'STTC': 159, 'NORM': 113, 'MI': 73, 'NONE': 19}, 'matched_on_broad_cardiac_category': 835, 'matched_on_sex': 999, 'matched_on_age_band': 997, 'rhythm_label_counts': {'SR': 766, 'AFIB': 77, 'none': 61, 'STACH': 30, 'SBRAD': 23, 'SARRH': 17, 'AFLT': 8, 'PACE': 6, 'AFLT,SVTAC': 2, 'BIGU,SR': 2, 'SARRH,SBRAD': 1, 'SR,TRIGU': 1, 'AFLT,SR': 1, 'AFIB,AFLT': 1, 'BIGU,SBRAD': 1}, 'matching_limitations': 'ECG matched on broad features only; different deidentified individual than the EHR.'}

## FHIR
- {'valid_bundle_rate': 1.0, 'resource_counts_total': {'Patient': 1000, 'Encounter': 1000, 'Condition': 12269, 'Observation': 31638, 'MedicationStatement': 18662, 'AllergyIntolerance': 1150, 'Procedure': 9658, 'Goal': 1171, 'CarePlan': 1000, 'DiagnosticReport': 2000}, 'reference_resolution_failures': 0, 'medication_rxnorm_coverage': 0.995, 'mean_resources_per_bundle': 79.55}

> Composite modalities may originate from different deidentified individuals. Research/software-testing dataset only.