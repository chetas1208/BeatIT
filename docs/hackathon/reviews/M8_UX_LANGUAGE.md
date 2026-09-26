# M8 UX & Clinical Language Review

Date: 2026-09-26  
Agent: #34 (UX/clinical language reviewer)  
Scope: Missing Piece UI (`web/components/twin/missing-piece/*`), scalar
comparison overlay (`web/components/twin/comparison/UncertaintyOverlay.tsx`),
and canonical `DISCLAIMER` enforcement on Missing Piece API responses
(`python/hearttwin/safety.py`, `missing_piece/contracts.py`, engine
limitations). Read-only review unless a critical safety copy violation is found.

## Executive verdict

| Gate | Result |
|---|---|
| No test-ordering language | **PASS** |
| Simulation / uncertainty framing | **PASS** |
| Table text alternatives (accessibility) | **PASS** (one non-blocking ID hygiene note) |

**Overall: PASS** for Tier-1 M8 UX and clinical-language boundaries. No code
changes were required.

This review covers language and table text alternatives only. It does not
clear numerical correctness, browser QA, or unrelated M8 math gates.

## Evidence reviewed

| Surface | Location | Role |
|---|---|---|
| Missing Piece panel | `web/components/twin/missing-piece/MissingPiecePanel.tsx` | Primary M8 copy, status/alert regions, result disclaimers |
| Sensitivity table | `web/components/twin/missing-piece/SensitivityTable.tsx` | Tabular sensitivity with caption and prose summary |
| Evidence map | `web/components/twin/missing-piece/EvidenceMap.tsx` | Ranked evidence cards (not a table) |
| Scalar overlay | `web/components/twin/comparison/UncertaintyOverlay.tsx` | M7 handoff; no geometric uncertainty claims |
| Canonical disclaimer | `python/hearttwin/safety.py:12-17` | Required response text |
| Response contract | `python/hearttwin/missing_piece/contracts.py:319-338` | `safety_disclaimer` must equal `DISCLAIMER` |
| Engine limitations | `python/hearttwin/missing_piece/engine.py:265-269` | Server-side rejection of IG / medical recommendation |
| Evidence ranking assumptions | `python/hearttwin/missing_piece/evidence_value.py:53-56` | Proxy labels, not care recommendations |
| Evidence taxonomy | `python/hearttwin/missing_piece/evidence.py:3-7,39-60` | Educational simulation proxy mapping |

## Gate 1 — No test-ordering language

**Result: PASS**

Reviewed user-visible strings and backend limitation text for imperatives or
care-path language that would tell a user to obtain, schedule, order, or
perform clinical measurements or tests.

**What is absent (required):**

- No phrases such as “order,” “obtain,” “schedule,” “perform,” “you should
  get,” “recommended test,” or “next step in care.”
- No information-gain or “probability that a test will help” wording (aligned
  with `docs/hackathon/M8_INFORMATION_GAIN_BOUNDARY.md`).

**What is present (acceptable under M8 boundary):**

- Panel intro: “uncertainty-impact heuristic, not a probability or
  information-gain estimate”
  (`MissingPiecePanel.tsx:86-88`).
- Evidence block: “deterministic priority heuristic, not a promise of benefit
  or an information-gain estimate” (`MissingPiecePanel.tsx:174`).
- Ranked items use **Priority** scores and `aria-label="Evidence priority
  ranking"` (`EvidenceMap.tsx:10-15`), not test-order verbs.
- Backend: “Evidence Priority Score is not expected information gain or a
  medical recommendation” (`engine.py:268`); evidence-value assumptions state
  labels are “educational proxy mappings, not medical recommendations”
  (`evidence_value.py:56`).

**Residual UX ambiguity (advisory, not a fail):**

- Section heading **“WHAT WOULD HELP?”** (`MissingPiecePanel.tsx:173`) can
  sound like care guidance in isolation. The immediately following sentence and
  engine limitations bound it to model-proxy prioritization. For a future
  polish pass, a heading such as “Which proxies would constrain uncertainty?”
  would reduce misread risk without changing behavior.

- `EvidenceMap` displays raw `evidence_type` identifiers (e.g.
  `echocardiographic_measurement`) rather than taxonomy `label` strings. That
  is awkward UX but avoids imperative clinical labels in the ranked list;
  rationales remain proxy-mapping language from the API.

## Gate 2 — Simulation uncertainty framing

**Result: PASS**

Copy consistently frames outputs as **deterministic model behavior**, **local
sensitivity**, and **heuristics**, not patient measurements, probabilities, or
clinical conclusions.

**Frontend:**

- Research lens badge and “WHY IS THIS UNCERTAIN?” frame (`MissingPiecePanel.tsx:84-88`).
- Results: “bounded local model responses, not clinical measurements or
  probabilities” (`MissingPiecePanel.tsx:149-150`).
- Drivers: “uncertainty-impact heuristic” (`MissingPiecePanel.tsx:160`).
- Table footer: local finite-difference responses; relative column is a
  “ranking heuristic, not a confidence measure, probability, or clinical
  conclusion” (`SensitivityTable.tsx:83-86`).
- Inline safety note plus canonical API disclaimer at footer
  (`MissingPiecePanel.tsx:182-185`).
- `UncertaintyOverlay`: “Model-proxy impact annotations; no geometric
  uncertainty is inferred” (`UncertaintyOverlay.tsx:19-21`).

**Backend / API:**

- `DISCLAIMER` states educational simulation only, not for diagnosis or
  treatment, not a medical device (`safety.py:12-17`).
- `MissingPieceResult` rejects non-canonical `safety_disclaimer` values
  (`contracts.py:334-338`); tests assert equality with `DISCLAIMER`
  (`test_missing_piece_api_models.py`, `test_missing_piece_engine_review.py`).
- Limitations list matches UI boundaries (local FD, heuristic impact, no IG,
  unavailable-not-imputed) (`engine.py:265-269`).

No diagnosis, treatment, efficacy, or “you have / you need” clinical assertions
were found in the reviewed M8 UI or Missing Piece response copy.

## Gate 3 — Table text alternatives (accessibility)

**Result: PASS**

M8 exposes one data table in this scope: `SensitivityTable`.

**Implemented alternatives:**

- Visually hidden `<caption>` summarizing table purpose
  (`SensitivityTable.tsx:35`).
- Column headers with `scope="col"`; parameter cells use `scope="row"`
  (`SensitivityTable.tsx:37-64`).
- Prose description linked via `aria-describedby="sensitivity-table-description"`
  explaining local responses, heuristic column, and unavailable cells
  (`SensitivityTable.tsx:33,83-87`).
- Unavailable numeric cells expose text “Unavailable (…)” rather than silent
  empty cells (`SensitivityTable.tsx:67-74`).

**Non-table M8 lists:**

- `EvidenceMap` uses an ordered card list with `aria-label="Evidence priority
  ranking"` — appropriate for non-tabular content; no table gate applies.
- `UncertaintyOverlay` uses `aria-label="Scalar uncertainty overlay"` and
  plain list text.

**Non-blocking note:**

- `sensitivity-table-description` is a fixed document id. Only one Missing
  Piece table is mounted in the current shell; if multiple tables were ever
  rendered on one page, ids should be scoped (e.g. `useId`) to avoid duplicate
  `aria-describedby` targets. This is hygiene, not missing text alternatives
  today.

## Prohibited language drift (would fail re-review)

- Replacing “heuristic,” “Priority,” or “model proxy” with “get this test,”
  “order labs,” “recommended workup,” or “next diagnostic step.”
- Presenting ranking scores as likelihood, confidence, or expected clinical
  benefit.
- Removing or paraphrasing the canonical `safety_disclaimer` on Missing Piece
  responses.
- Describing sensitivity or evidence rank as diagnosis, treatment advice, or
  patient-specific care optimization.

## Validation references

- `python/hearttwin/tests/test_missing_piece_api_models.py` — canonical
  disclaimer on response DTOs.
- `python/hearttwin/tests/test_missing_piece_engine_review.py` — disclaimer on
  engine output.
- `docs/hackathon/M8_INFORMATION_GAIN_BOUNDARY.md` — measurement-recommendation
  boundary (documentation aligns with reviewed copy).

## Conclusion

M8 Missing Piece UI and overlay copy **PASS** the three reviewed gates: no
test-ordering language, strong simulation/uncertainty framing, and adequate
table text alternatives for `SensitivityTable`. Canonical `DISCLAIMER` usage on
Missing Piece responses is enforced in contracts and surfaced in the panel.
No critical safety copy violation was found; no production strings were changed.
