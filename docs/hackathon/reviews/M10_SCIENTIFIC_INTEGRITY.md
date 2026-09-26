# M10 scientific-integrity and provenance review

Date: 2026-09-26 UTC
Scope: BeatIT/ DualBeat simulation surface, including API contracts, the M9
product UI, release/demo documentation, and adjacent feature-flagged copy.
Disposition: **OPEN — do not make a public clinical-data or clinical-use claim**

This is a language and labeling audit, not a clinical validation. It checks
whether a reader can distinguish observed input, deterministic derivation,
simulation, priors, hypothetical branches, and synthetic demo data without
being led toward a diagnosis, treatment recommendation, clinical measurement
claim, or patient-specific probability claim.

## Canonical boundaries reviewed

- `python/hearttwin/safety.py:12-18` defines the canonical disclaimer:
  “Educational cardiac simulation only. Not for diagnosis or treatment
  decisions.” It further states that DualBeat is not a medical device, does not
  provide medical advice, and emits simulated educational estimates.
- `python/hearttwin/api.py:153-225` applies the disclaimer to liveness,
  readiness, system-status, intelligence-status, and model-status responses.
  The ensemble and Shadow Trial response models also carry a disclaimer.
- `web/components/safety/DisclaimerModal.tsx:54-70` presents the non-device,
  non-diagnosis, non-treatment boundary and says that outputs are simulated
  estimates. `web/components/product/ReportSurface.tsx:42-59` repeats the
  boundary in the report and keeps a source-status legend and interpretation
  boundaries visible.
- `web/lib/product/sourceStatus.ts` and
  `web/components/product/SourceStatusBadge.tsx` expose the distinctions
  `OBSERVED`, `DERIVED`, `SIMULATED`, `PRIOR`, and `SYNTHETIC`.
- `python/hearttwin/ensemble.py:98-109` rejects synthetic replay provenance
  when an ensemble request claims `origin_quality="observed"`.
  `python/hearttwin/ensemble.py:441-458` labels the ensemble as simulation and
  states that percentile spread is not a clinical confidence interval.
- `docs/hackathon/M10_SCOPE_FREEZE.md:36-45`,
  `docs/demo/JUDGE_QA.md:3-43`, and `docs/demo/DEMO_SCRIPT.md:20-42` preserve
  the nonclinical scope, synthetic-demo labeling, deterministic authority, and
  the instruction not to call a simulated difference a clinical benefit or
  harm.

These controls are substantively aligned. They do not by themselves establish
clinical validity, regulatory compliance, patient-data safety, or calibration.

## Findings

| ID | Severity | Finding and evidence | Disposition |
|---|---|---|---|
| SI-01 | P1 | The README says “Every API response carries a mandatory disclaimer” (`README.md:40-41`). The API only adds the canonical disclaimer in selected success models and selected Shadow Trial error handlers (`python/hearttwin/api.py:1293-1327`); non-Shadow `HTTPException` and request-validation errors delegate to FastAPI’s default handlers. A consumer can therefore receive an error without the boundary language. | **OPEN.** Either make the response invariant true for every public route and error envelope, or narrow the documentation claim. Add route-wide tests for 2xx, 4xx, 404, 422, and 5xx paths. |
| SI-02 | P1 | Provenance vocabularies are not a single enforced contract. `python/hearttwin/schemas.py:70-86` uses `file_extraction`, `user_input`, `default_model_prior`, and `derived`; `python/hearttwin/ensemble.py` uses `observed`, `derived`, `interpolated`, and `synthetic`; the assistant schema defines a separate canonical enum (`python/hearttwin/assistant/schemas.py:45-79`) and explicitly says mapping is deferred. The frontend adds `simulated` and `prior` (`web/lib/product/sourceStatus.ts`). | **OPEN.** Before public release, publish and test one explicit crosswalk. Every displayed status must have a lossless source meaning; `file_extraction` must not silently become `observed`, and a prior or simulation must never render as measured evidence. |
| SI-03 | P1 | The product navigation calls the Twin space “Observed state” (`web/lib/product/contracts.ts:25-30`) and the report calls its section “Observed twin” (`web/lib/product/reportContracts.ts:46-48`) whenever state and visualization exist. The report input carries only source IDs (`web/lib/product/reportContracts.ts:21-31`); it does not carry per-field provenance into the section label. A state containing derived values, priors, or synthetic replay can therefore be read as wholly observed. | **OPEN.** Use a qualified label such as “Source-backed and derived twin” and show the selected state’s field-level source summary. Keep `OBSERVED` as a value-level status only when the backend provenance says so. |
| SI-04 | P1 | README copy uses “clinical readout” and “for radiologists & cardiologists” (`README.md:28-29`) while also describing “forecasts” and “recovery trajectories” (`README.md:3,34-38`). The same page contains a strong disclaimer, but this audience/wording combination can imply clinical suitability or predictive performance. | **OPEN.** Change public-facing copy to “educational readout,” “reference terminology,” and “bounded simulated trajectories,” or pair any specialist audience language with an immediate explicit nonclinical qualifier. Do not claim clinical utility, diagnostic performance, or forecast accuracy. |
| SI-05 | P1 | The repository contains an adjacent, feature-flagged CareGuard surface whose README copy says “clinician-facing” and “Clinical decision support draft. Clinician and pharmacist review required” (`README.md:154-160`). This is a different product boundary from the frozen five-space BeatIT simulation. If enabled or shown in a demo, it can be mistaken for the same validated cardiac product. | **OPEN for integration.** Keep the CareGuard flag disabled for the BeatIT release candidate, verify its routes and navigation are absent in the demo configuration, and avoid presenting its clinical-support language as evidence about BeatIT. Audit it separately if it is intended for public deployment. |
| SI-06 | P2 | The modal disclaimer is acknowledged in `localStorage` (`web/components/safety/DisclaimerModal.tsx:11-24,39-47`) and can disappear after acknowledgement. The report currently repeats the disclaimer, which is a useful defense, but other product surfaces must not rely on the modal as their only safety label. | **PASS with release check.** Preserve response-level disclaimers and persistent context-appropriate labels. Test a fresh session, an acknowledged session, private-storage failure, direct deep link, and report rendering. |
| SI-07 | P2 | The final architecture correctly limits local/provider-neutral models to explanation and extraction and says they never calculate physiology (`docs/ARCHITECTURE_FINAL.md:19-29`). The demo and judge Q&A likewise state that deterministic Python owns numeric outputs and that uncertainty is descriptive rather than a probability or clinical risk estimate. | **PASS.** Retain these statements in the release bundle and ensure model errors/fallback text cannot replace them with authoritative-sounding language. |

## Provenance interpretation rules for the release candidate

The following meanings are safe for the current architecture and should remain
visible wherever the corresponding value is shown:

| Label | Permitted interpretation | Must not be presented as |
|---|---|---|
| `OBSERVED` / source-backed extraction | A value supplied by the selected input or explicitly reported in it, with source and method retained. | A validated diagnosis, a complete patient history, or a directly measured value when the actual input was only an extracted/report label. |
| `DERIVED` | A deterministic value calculated from declared inputs and a named formula. | An independent measurement or a model-validated clinical result. |
| `PRIOR` / `default_model_prior` | An explicit population/model assumption used because input was missing. | Patient evidence, a patient-specific estimate, or a calibrated probability. |
| `SIMULATED` / hypothetical branch | A deterministic output under a declared scenario or parameter perturbation. | A treatment effect, clinical benefit/harm, recovery prediction, or recommendation. |
| `SYNTHETIC` | Demo/replay/generated data that is not patient evidence. | Observed history, a real patient case, or validation evidence. |
| uncertainty spread / confidence-like quality field | A bounded descriptive quality or spread indicator whose definition is shown. | A posterior, confidence/credible interval, clinical risk, or probability of an outcome. |

The labels must travel with the value or artifact, not only appear in a global
legend. A source ID without its kind, method, and limitations is an audit
pointer, not proof of observation.

## Required verification before release

1. Exercise every public API route and representative error path and assert the
   canonical `safety_disclaimer`, or remove the README’s universal-response
   claim. Include generic 404/422/500 responses, not only Shadow Trial routes.
2. Add a contract-level provenance crosswalk test covering backend
   `ValueSource`, ensemble `origin_quality`, assistant `CanonicalProvenanceKind`,
   and frontend source-status labels. Include a negative test that synthetic
   replay cannot render as observed.
3. Render the report with observed, derived, prior, simulated, and synthetic
   fixtures. Verify that no fixture receives the unqualified “Observed twin”
   label and that source kind remains visible next to the relevant value.
4. Search user-facing strings and demo narration for unqualified clinical
   claims (`diagnosis`, `treatment`, `clinical`, `patient-specific`, `forecast`,
   `benefit`, `harm`, `risk`, `probability`, `confidence interval`). Review each
   hit in context; safety disclaimers and audit documentation are allowed, but
   product copy must not imply authority.
5. Run the demo with `CAREGUARD_ENABLED` and
   `NEXT_PUBLIC_CAREGUARD_ENABLED` disabled. Confirm the five-space BeatIT flow
   cannot route to or visually conflate the adjacent CareGuard surface.
6. Confirm local-model, VISTA, network-offline, and fallback responses retain
   the same educational boundary and never turn “available” or “loaded” into a
   claim of clinical validation.

## Final disposition

The deterministic core, safety gate, synthetic replay guard, report limitations,
and demo wording provide a credible nonclinical foundation. The scientific
integrity gate is nevertheless **not closed** because SI-01 through SI-05 can
create an accidental authority or provenance reading at the API, UI, or public
documentation boundary. No production changes were made in this review.
