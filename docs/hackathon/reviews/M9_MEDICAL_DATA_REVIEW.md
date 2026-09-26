# M9 Medical Data and Safety Review

Date: 2026-09-26  
Scope: adversarial, read-only review of the M9 five-space journey and shared
intake, report, assistant, trace, and artifact surfaces. Focus: safety
disclaimer, diagnosis/treatment/emergency blocking, patient-data exposure, and
computational-versus-clinical wording. No production or test files were changed.

## Verdict

**NO-GO for patient data; CONDITIONAL for synthetic/demo use only.**

The repository has meaningful positive controls: a canonical backend disclaimer,
request blocking, model-output blocking in the Copilot path, explicit
hypothetical/simulated language on Experiment and Compare, and bounded
uncertainty wording on Evidence. They do not form a complete M9 medical-data
boundary. The public-facing case and artifact APIs are unauthenticated, CORS is
permissive, case payloads can contain patient notes and clinical state, and the
M9 UI can label synthetic or replayed state as `OBSERVED`. A user can also
dismiss the only global disclaimer for future sessions.

Until the findings below are closed, the only defensible operating policy is
synthetic, non-identifiable demo data with no clinical reliance.

## Evidence inspected

- M9 contracts: `docs/hackathon/M9_INFORMATION_ARCHITECTURE.md`,
  `M9_PRODUCT_STATE.md`, `M9_HUMAN_FACTORS.md`, and `M9_PREFLIGHT.md`.
- M9 surfaces: `web/components/layout/AppShell.tsx`,
  `web/components/intake/CaseIntakePanel.tsx`,
  `web/components/product/ReportSurface.tsx`,
  `web/components/heart/HeartScene.tsx`, and Experiment, Compare, and
  Evidence panels.
- Safety/data paths: `python/hearttwin/safety.py`,
  `python/hearttwin/api.py`, `python/hearttwin/schemas.py`,
  `python/hearttwin/tools/storage.py`, and
  `python/hearttwin/tools/weave_trace.py`.
- Prior scoped evidence: `docs/hackathon/M5_5_SECURITY_CREDIBILITY_REVIEW.md`
  and the M9 Evidence, Experiment, and Report reviews.

No browser, deployment, authorization, or live-network verification is claimed.

## Findings

### MED-1 — Public case/artifact access is incompatible with patient data — P0, open

`python/hearttwin/api.py:111-117` enables `allow_origins=["*"]` with
`allow_credentials=True`. Case, trace, harness, ensemble, Shadow Trial, and
Missing Piece routes do not establish authentication, authorization, case
ownership, or tenant isolation. `GET /api/v1/cases/{case_id}` returns the
stored `CaseRecord` directly (`api.py:730-735`); trace and harness routes
expose retained run material (`api.py:738-756,857-886`).

The M9 intake deliberately accepts patient notes and uploads
(`CaseIntakePanel.tsx:4-15,500-584,632-648`). A caller who obtains or guesses
an ID can therefore request notes, filenames, source metadata, validated fields,
and state. The prior M5.5 review also recorded the unauthenticated/wildcard-CORS
exposure and a live preflight observation.

**Disposition:** Keep the deployment synthetic-only. Before real data is
permitted, add authentication and object-level authorization, restrict CORS to
explicit origins, validate artifact parent/owner on every fetch, and fail closed
for unknown or unauthorized IDs.

### MED-2 — Stored and returned payloads are not minimized to the M9 need — P0, open

`PatientContext.notes` is part of `CardiacTwinState`
(`python/hearttwin/schemas.py:99-106,248-264`), and `CaseRecord` retains
`patient_notes` and uploaded-file metadata (`schemas.py:338-360`). Case
state is serialized to Redis or process memory without field-level minimization
(`python/hearttwin/tools/storage.py:75-97`). The case-detail response returns
that record as-is. Ensemble responses include sampled state, so patient-context
fields can enter ensemble persistence and responses; the M5.5 review reproduced
this with note/CT sentinels.

Trace sanitization is best effort. `weave_trace.py:20-36,291-335` matches
exact denylisted keys, truncates strings, and preserves upload metadata. It does
not prove that arbitrary evidence/provenance fields are non-sensitive and
preserves filenames, which can contain names or encounter identifiers. The
local trace and SSE routes expose retained traces (`api.py:738-845`).

**Disposition:** Do not send real notes, scans, filenames, or identifiable
vitals to the current deployment. Define minimized DTOs, exclude notes/CT/raw
evidence from ensemble and trace payloads, use opaque non-semantic identifiers,
and add retention/deletion and redaction tests.

### MED-3 — The canonical disclaimer is not a stable, always-visible M9 contract — P1, open

The canonical backend value is defined in `python/hearttwin/safety.py:12-17`
and includes educational-only, non-diagnosis, non-treatment, non-medical-device,
and simulated-estimate language. Most successful routes attach it, and the
ensemble/Shadow Trial contracts validate it.

The M9 report has weaker paths:

- `web/lib/product/reportContracts.ts:42-45` falls back to
  `"Educational simulation only; not for diagnosis or treatment decisions."`,
  which is not the canonical value and omits medical-device, medical-advice,
  and simulated-estimate clauses.
- `web/components/safety/DisclaimerModal.tsx:4-8,25-43` stores acknowledgement
  in localStorage and removes the boundary from subsequent sessions.
  `AppShell.tsx:247` mounts it globally, but TWIN, EXPERIMENT, COMPARE, and
  EVIDENCE have no persistent visible canonical banner after dismissal.
- `web/lib/api.ts:53-106` treats `safety_disclaimer` as optional on errors,
  while many FastAPI `HTTPException` paths return only `detail`.

**Disposition:** Use one canonical value on success and error responses. Keep a
compact visible safety label on all five spaces; acknowledgement must be an
additional disclosure, not the only durable control.

### MED-4 — Blocking exists at selected boundaries, not at the final M9 display boundary — P1, open

`python/hearttwin/safety.py:24-54` blocks diagnosis, treatment, medication,
emergency/triage, and clinical request patterns. Case creation applies it to
patient notes (`api.py:707-727`), and the Copilot path checks both question
and generated answer (`python/hearttwin/copilot.py:418-463`). Tests cover
representative diagnosis, treatment, and emergency cases.

This is not a universal output gate for M9. The frontend renders persisted or
authority-owned text directly: findings summaries and rhythm labels
(`HeartScene.tsx:1129-1174`), scenario descriptions and warnings
(`ScenarioInspector.tsx:114-131`), ensemble assumptions/warnings
(`PlausibleTwinsPanel.tsx:117-121`), and report summaries
(`ReportSurface.tsx:49-59`). No shared final-display validator protects these
strings. Blocking input does not prove that uploaded report text, extracted
labels, stored warnings, or future payloads remain safe after rendering.

**Disposition:** Add one backend final-output validator for all user-facing
narrative fields, reject unsafe persisted payloads, and test adversarial
paraphrases plus uploaded-source text. Do not rely on a browser-only filter.

### MED-5 — TWIN can present replay/synthetic state with an OBSERVED badge — P0, open

`AppShell.tsx:107-113` assigns TWIN the literal `"observed"` status,
independent of the selected snapshot's quality. Replay content is possible:
`HeartScene.tsx:1084-1087` renders `REPLAY · DEMO STREAM`, and
`web/lib/twin/replay/index.ts:59-65` marks replay quality as `synthetic`.
The same state can therefore be shown as both synthetic/replay and
`OBSERVED`.

This is a lineage error, not just a cosmetic issue. M9 requires observed,
derived, simulated, prior, and synthetic material to remain distinct
(`M9_INFORMATION_ARCHITECTURE.md`, navigation and acceptance sections).

**Disposition:** Derive the badge from authoritative snapshot/artifact quality.
If lineage is absent or mixed, show an unavailable or conservative synthetic
status; never default to observed.

### MED-6 — Intake copy invites clinical-looking data without a prominent data-safety boundary — P1, open

The intake accepts “labs, ECG, or imaging,” asks for “Symptoms, history, and
context,” and says “The AI reads vitals from your files and notes”
(`CaseIntakePanel.tsx:517-583,632-648`). Golden-case labels include
`HFrEF + CKD`, `Post-MI ischemic`, and `Dilated cardiomyopathy`
(`CaseIntakePanel.tsx:77-125`). The source comment says these are not real
patients, but that protection is not consistently visible in the selector or
notes field. The explicit synthetic warning is attached only to random-vitals
generation (`CaseIntakePanel.tsx:780-797`), not upload/free text.

**Disposition:** Put “synthetic/demo data only — do not upload identifiable
patient data” beside upload and notes controls. Mark every preset as
`SYNTHETIC DEMO CASE` and remove reliance-oriented language.

### MED-7 — Computational surfaces use clinically authoritative framing — P1, open

Positive controls exist: Experiment says `HYPOTHETICAL SIMULATION` and that
observed history is unchanged (`ScenarioPanel.tsx:21-27`); Compare says
paired visual projection only and not diagnosis/treatment guidance
(`SplitHeartComparison.tsx:87-91`); Evidence calls its score an
uncertainty-impact heuristic, not probability or information gain
(`MissingPiecePanel.tsx:84-89,145-185`).

The boundary is weakened elsewhere:

- `HeartScene.tsx:1129-1130` describes findings as a readout “for a
  clinician,” while showing region, severity, AHA/coronary codes, and EF
  threshold copy.
- `web/lib/heart/patient/adapter.ts:20-21,167-170` uses “patient-specific”
  wording even when state may be synthetic or replayed.
- `ReportSurface.tsx:42-47` calls the first section “Observed twin” from an
  in-memory boolean, and `reportContracts.ts:47-51` marks Evidence ready
  whenever an ensemble exists rather than when a matching analysis exists.
- `PhysicianBriefView.tsx:171-176` presents “Physician decision support” and
  `clinical_context`; it is not the main M9 route, but is reachable and can
  blur the educational boundary.

**Disposition:** Require source-qualified computational wording and per-section
lineage/method/limitation metadata. Do not infer clinical readiness from object
presence.

## Surface disposition matrix

| M9 surface | Medical-data result | Wording result | Disposition |
| --- | --- | --- | --- |
| TWIN / intake | Raw notes/files accepted; APIs not authorized | Replay can be labeled OBSERVED; clinical presets are prominent | **NO-GO for real data** |
| EXPERIMENT | Synthetic-only until artifact authorization exists | Strong hypothetical copy, but persisted narratives lack a final display gate | **Conditional synthetic-only** |
| COMPARE | Pair data depends on unauthenticated artifact reads | Baseline/counterfactual is mostly clear | **Conditional synthetic-only** |
| EVIDENCE | Analysis/ensemble access is not authorized | Heuristic wording is strong but not globally carried | **Open integration** |
| REPORT | In-memory state and shared IDs are not a clinical record boundary | Fallback disclaimer and “Observed twin” are unsafe | **Open** |

## Required closure gates

M9 medical/data review should not move to PASS until there is evidence for:

1. Authentication, authorization, ownership checks, restrictive CORS, and safe
   unauthorized/not-found behavior for every case and artifact read.
2. Minimized case, ensemble, trace, SSE, report, and Weave payloads with
   retention/deletion policy and adversarial filename/note/evidence redaction
   tests.
3. One canonical disclaimer on success and error responses plus a visible
   compact safety label on all five M9 spaces after modal acknowledgement.
4. A final backend display-content validator covering diagnosis, treatment,
   medication, emergency, triage, and paraphrased clinical-authority language.
5. Authoritative source-status propagation; no unconditional OBSERVED default and
   no report readiness from booleans.
6. Intake copy that clearly rejects identifiable patient data in the current
   deployment and labels every preset synthetic/demo.

## Verification record

This is a source-level review only. The workspace was already dirty with
unrelated M5.5–M9 changes. No production or test file was modified, and no
browser or live deployment check was used as completion evidence. The review
file itself is the only file authorized for this task.
