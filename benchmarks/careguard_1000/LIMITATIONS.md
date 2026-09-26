# Limitations

- **Not a clinical-validation study.** This benchmark measures software behavior
  on de-identified, synthetic, or composite open-data cases. Nothing here is a
  claim about clinical safety, efficacy, or fitness for diagnosis or treatment.

- **Silver reference labels.** Primary labels are *source-derived* — computed
  deterministically from case facts, RxNorm normalization, and openFDA drug
  labels. They are not clinician-adjudicated. A stratified subset is queued for
  human adjudication to form a gold subset; until that is completed, headline
  numbers are against the silver set and are described as such.

- **openFDA label coverage is partial.** A medication without a matched openFDA
  label yields no `contraindication_signal` reference assertion for that drug —
  absence in the reference is "not established by our sources", not "safe".
  Contraindication-signal recall is therefore conditional on label coverage.

- **Allergy matching is ingredient/string based.** Allergy-vs-drug reference
  matches use RxNorm ingredient overlap and normalized-name matching. Cross-
  reactivity classes (e.g. sulfa, beta-lactam families) are only partially
  captured, so allergy-conflict recall is a lower bound on true clinical
  cross-reactivity.

- **Track 2 does not isolate model intelligence.** The end-to-end comparison
  pits a standalone-model workflow against a full agentic system with
  normalization, retrieval, a deterministic conflict engine, and a critic. A
  difference there reflects the whole system, not the base model alone. Track 1
  is the controlled comparison.

- **CareGuard arm uses the deterministic engine.** Arm E is the production
  medication-safety engine (`build_multimorbidity_output`) run offline; its
  optional LLM prose stages are not exercised. This makes the arm reproducible
  and free but means the arm reflects CareGuard's deterministic safety logic,
  not any model-generated narrative.

- **Composite modality caveat.** Where a case links a PTB-XL ECG to an eICU
  record, the ECG and EHR are from different de-identified individuals and are
  combined only for multimodal software testing. The medication-safety task
  does not depend on the ECG.

- **No seed determinism for model arms.** The Messages API is not
  seed-reproducible; identical requests can vary. Reliability is measured with
  repeated trials rather than assumed.

- **Sampling identical, not tuned.** The comparison omits sampling parameters
  for both models to keep requests identical. It does not search for the best
  per-model prompt; it measures the models under one shared, reasonable prompt.
