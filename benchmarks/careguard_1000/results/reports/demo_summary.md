# CareGuard benchmark — proof summary

> Research benchmark using deidentified, synthetic, or composite open-data cases. Not a clinical-validation study and not for diagnosis or treatment decisions. Where a case links a PTB-XL ECG to an eICU record, the ECG and EHR originate from different deidentified individuals and are combined only for multimodal software testing.

- **CareGuard (Arm E)** graded on **1000** cases; composite 0.458, medication recall 100.0%, schema-valid 100.0%, cost/case $0.0000.
- **system_vs_model_46**: careguard_full 0.594 vs sonnet_46_case_only 0.683 (Δ -0.090, n/a, n=3).
- **ablation_conflict_engine**: careguard_full 0.458 vs careguard_no_deterministic_conflict_engine 0.205 (Δ 0.253, p=1.48e-121, n=1000).
- **ablation_retrieval**: careguard_full 0.458 vs careguard_no_retrieval 0.458 (Δ 0.000, n/a, n=1000).

Full tables, CIs, subgroup and failure analysis in `results/reports/report.md` / `.html` / `.pdf`.
