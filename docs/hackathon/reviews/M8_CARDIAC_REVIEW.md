# M8 Cardiac Physiology Review — Missing Piece Evidence & Perturbations

Status: **review recorded**  
Date: 2026-09-26  
Agent: **Agent 32 — Cardiac Physiology Reviewer (M8 Missing Piece)**  
Scope: `evidence_map.py`, `perturbations.py`, `evidence.py`, and perturbation /
evidence-priority sections of `docs/hackathon/M8_MATH_AUDIT.md`. Read-only;
no Python changes.

## Executive result

For **Tier-1 hackathon scope** (five bounded proxy inputs, educational
simulation, explicit non–information-gain labeling), the evidence taxonomy and
perturbation policy are **defensible as reviewed proxy heuristics**. Perturbation
math and domain handling **align with the M8 math audit** and **`PARAMETER_BOUNDS`**.

Adversarial gaps are mostly **physiological oversimplification** and **governance
/ caller-integrity** items, not silent clinical claims inside these modules.
Nothing here warrants blocking Tier-1 on its own, provided UI and API callers
keep `EDUCATIONAL_SCOPE`, Evidence Priority Score naming, and reviewed
constraint strengths.

## Evidence inspected

| Artifact | Role |
|---|---|
| `python/hearttwin/missing_piece/evidence_map.py` | Allowlisted evidence→parameter map, strength weights, priority score inputs |
| `python/hearttwin/missing_piece/evidence.py` | Versioned taxonomy, default constraints, educational scope string |
| `python/hearttwin/missing_piece/perturbations.py` | Bounded finite-difference step and in-domain points |
| `python/hearttwin/ensemble.py:22-28` | Authoritative `PARAMETER_BOUNDS` |
| `docs/hackathon/M8_MATH_AUDIT.md:129-178` | Tier-1 perturbation size and difference scheme |
| `docs/hackathon/M8_MATH_AUDIT.md:300-326` | Evidence Priority Score boundary |

Cross-check only (not in scope file list): `python/hearttwin/missing_piece/sensitivity.py:137-140`
duplicates the same step formula without importing `perturbations.py` — drift
risk if one path changes.

## Findings — evidence-to-parameter mappings

| ID | Area | Result | Finding |
|---|---|---|---|
| E1 | Map completeness vs model | **PASS** | All five ensemble proxies appear in the reviewed map: `preload_index` + `contractility_index` (`evidence_map.py:24-27`, `evidence.py:43-44`), `afterload_index` + `systemic_vascular_resistance_index` (`evidence_map.py:28-31`, `evidence.py:50-51`), `heart_rate_bpm` (`evidence_map.py:32`, `evidence.py:57-58`). No orphan parameters within the five-dimensional proxy space. |
| E2 | Taxonomy ↔ allowlist sync | **PASS** | Parameter tuples and evidence type keys match between `EVIDENCE_PARAMETER_MAPPINGS` (`evidence_map.py:22-34`) and `EVIDENCE_TAXONOMY` (`evidence.py:39-61`). Tests lock this (`test_missing_piece_evidence_map.py:38`, `test_missing_piece_evidence.py:19-23`). |
| E3 | Undeclared / smuggled mappings | **PASS** | Unknown evidence types fail closed (`evidence_map.py:61-67`). Parameters not in the allowlist for a type are rejected (`evidence_map.py:69-75`). Subset selection preserves reviewed order (`evidence_map.py:76`, `mapped_parameters` tests). |
| E4 | Echo → preload + contractility | **CONDITIONAL** | Mapping is **coarse but acceptable** for a two-index hemodynamic toy model. Real echocardiography informs filling, contractility, valvular disease, and wall motion; only two proxies exist. Module header correctly disclaims unique identifiability (`evidence_map.py:3-6`). Rationale stays at proxy language (`evidence.py:45`). **Risk:** product copy that says “echo measures contractility” without “proxy” reads clinical; keep `EDUCATIONAL_SCOPE` visible (`evidence.py:17`, `evidence.py:36-37`). |
| E5 | BP series → afterload + SVR | **CONDITIONAL** | Cuff / line pressures **conflate** CO, SVR, and arterial compliance; separating `afterload_index` and `systemic_vascular_resistance_index` from pressure alone is **not identifiable** without additional measurements. Dual mapping is honest as “intended proxies” (`evidence.py:52`) but **double-counts** in priority scoring: one `blood_pressure_series` constraint contributes twice in `build_priority_inputs` (`evidence_map.py:127-139`) with the same strength weight per parameter. That inflates BP evidence vs single-parameter types (e.g. `repeat_ecg`) without implying two independent experiments. Acceptable for Tier-1 if labeled heuristic; not a physiology claim. |
| E6 | Repeat ECG → heart rate only | **CONDITIONAL** | Rate from ECG is the **only** defensible link to `heart_rate_bpm` in this model. Rhythm, conduction, ischemia, and QT are absent from `PARAMETER_BOUNDS`. Mapping is **narrow by necessity**, not an assertion that ECG is only HR (`evidence.py:59`). |
| E7 | Strength weights vs audit | **PASS** | `STRENGTH_WEIGHTS` (`evidence_map.py:36-37`) matches Tier-1 table in `M8_MATH_AUDIT.md:304-309`. Priority aggregation matches audited formula (`evidence_map.py:138`, `map_evidence_scores` docstring `evidence_map.py:150-154`; audit `M8_MATH_AUDIT.md:314-317`). |
| E8 | Taxonomy default strengths | **PASS (defaults)** | Reviewed defaults: echo `strong`, BP and ECG `moderate` (`evidence.py:44`, `50`, `58`). These feed `DEFAULT_EVIDENCE_CONSTRAINTS` (`evidence.py:78-80`). |
| E9 | Caller-overridden strength | **CONDITIONAL** | `EvidenceConstraint.strength` is not tied to taxonomy when callers build custom constraints (`contracts.py:189`; no cross-check in `evidence_map.py`). A caller could mark `repeat_ecg` as `direct` (weight `1.0`) despite taxonomy `moderate`. **Not a bug in the map**, but a **review integrity** gap for anything beyond `evidence_constraints()`. |
| E10 | Information gain / care claims | **PASS** | Scoring docstring rejects information gain (`evidence_map.py:152-153`). Taxonomy text avoids diagnose/treat/prescribe (enforced in `test_missing_piece_evidence.py:39-46`). Audit forbids care promises (`M8_MATH_AUDIT.md:321-326`). |
| E11 | Version governance | **CONDITIONAL** | `EVIDENCE_MAP_VERSION = "m8-evidence-map-v1"` is duplicated in `evidence_map.py:18` and `evidence.py:15`. Divergent edits could ship mismatched taxonomy vs scorer. Prefer single import or contract test beyond string equality. |

## Findings — perturbation ranges vs `PARAMETER_BOUNDS`

| ID | Area | Result | Finding |
|---|---|---|---|
| P1 | Bounds authority | **PASS** | All perturbations resolve bounds via `PARAMETER_BOUNDS` only (`perturbations.py:16`, `32-38`). Unknown parameters raise (`perturbations.py:37-38`). Matches audit parameter table (`M8_MATH_AUDIT.md:63-69`, `ensemble.py:22-28`). |
| P2 | Tier-1 step formula | **PASS** | Audit: `Q_i = max(abs(θ_i), 0.5 R_i)`, `h0_i = 0.05 Q_i`, `h_i = min(h0_i, 0.05 R_i)` (`M8_MATH_AUDIT.md:153-157`). Code: fractional `scale = max(abs(baseline), 0.5 * parameter_range)` (`perturbations.py:131-132`), `raw_step = step * scale` with default `step=0.05` (`perturbations.py:22-23`, `125-132`), cap `min(..., max_range_fraction * range)` with default `0.05` (`perturbations.py:23`, `122-123`, `134-137`). Defaults match audit five-percent Tier-1 policy (`M8_MATH_AUDIT.md:160-165`). |
| P3 | In-domain evaluation | **PASS** | `validate_baseline` enforces `L ≤ baseline ≤ U` (`perturbations.py:41-50`). `points()` nulls out-of-domain sides (`perturbations.py:145-152`), yielding central / forward / backward / unavailable (`perturbations.py:64-71`, `139-153`). Aligns with audit one-sided rules (`M8_MATH_AUDIT.md:167-174`). |
| P4 | Step positivity and cap policy | **PASS** | Rejects non-finite, non-positive steps (`perturbations.py:26-29`, `101-103`). Fractional step capped at 1 (`perturbations.py:106-107`). `max_range_fraction ∈ (0, 0.5]` (`perturbations.py:108-110`) prevents steps larger than half the declared range in one hop. |
| P5 | Absolute mode | **CONDITIONAL** | `absolute` mode uses native `step` then still applies the **5% range cap** (`perturbations.py:129-130`, `134-137`). Tests confirm (`test_missing_piece_perturbations.py:20-25`). Physically meaningful for indices but **not** the default engine path (`engine.py:113` uses fractional defaults). Document if absolute mode is exposed to users. |
| P6 | Bound edge detection | **CONDITIONAL** | `at_lower_bound` / `at_upper_bound` use exact equality (`perturbations.py:74-81`). Sampled floats rarely sit exactly on `L` or `U`; metadata flags may be wrong while `points()` still selects a valid one-sided scheme. **Numerical presentation** issue, not domain violation. |
| P7 | Parameter-specific spot checks | **PASS** | HR range 170 → max step `0.05 * 170 = 8.5` at high baseline (`test_missing_piece_perturbations.py:16-17`). Preload at `0.0`: forward-only with absolute step (`test_missing_piece_perturbations.py:28-39`). Contractility upper `1.5` matches `PARAMETER_BOUNDS` (`ensemble.py:26`). |
| P8 | Parallel implementation | **CONDITIONAL** | `run_local_sensitivity` in `sensitivity.py:137-140` reimplements the same `min(0.05*scale, 0.05*span)` logic without `PerturbationPolicy`. Math is consistent today; **future drift** is the risk. Out of scoped files but relevant for M8 integration hygiene. |

## Findings — unsupported or overstated clinical claims

| ID | Area | Result | Finding |
|---|---|---|---|
| C1 | Module-level disclaimers | **PASS** | Evidence map: “reviewed proxy map”, not unique identification (`evidence_map.py:3-6`). Taxonomy: educational simulation only (`evidence.py:3-6`, `17`). Perturbations: local finite differences, domain respect (`perturbations.py:1-7`). |
| C2 | Taxonomy labels | **CONDITIONAL** | Human labels (“Echocardiographic measurement”, “Blood-pressure series”, “Repeat ECG”) (`evidence.py:42`, `49`, `56`) resemble real modalities. Rationales correctly say “Maps … to … proxies” (`evidence.py:45`, `52`, `59`). **Fail** only if UI omits `EDUCATIONAL_SCOPE` / disclaimer — not if strings are shown with scope (`completeness.py:73-77` limitations are the right pattern for downstream). |
| C3 | Priority score naming | **PASS** | `map_evidence_scores` and audit require “Evidence Priority Score”, not information gain or care benefit (`evidence_map.py:150-154`, `M8_MATH_AUDIT.md:320-326`). |
| C4 | Implicit diagnostic utility | **CONDITIONAL** | Ranking uses uncertainty-impact × strength (`evidence_map.py:138`). High scores could be read as “get this test next” unless UI repeats audit language (`M8_MATH_AUDIT.md:324-326`). Code does not claim diagnosis; **presentation** is the hazard. |
| C5 | Strength semantics | **CONDITIONAL** | `strong` / `moderate` on echo and BP (`evidence.py:44`, `50`) are **reviewer-assigned weights**, not literature-derived likelihood ratios. Acceptable for hackathon; must not be narrated as clinical evidence quality in product copy. |

## Disposition summary

| Category | Pass | Conditional | Fail |
|---|---:|---:|---:|
| Evidence-to-parameter mappings | 5 | 5 | 0 |
| Perturbations vs bounds / audit | 5 | 3 | 0 |
| Clinical / care claims (in-module) | 2 | 3 | 0 |

No **FAIL** findings in the scoped modules: nothing asserts diagnosis, treatment,
identifiability, or information gain. **CONDITIONAL** items are explicit tradeoffs
for a five-proxy demo twin (coarse echo/BP mapping, dual-parameter BP scoring,
caller-defined strength, version duplication, bound-equality metadata).

## Bounded verdict — Tier-1 hackathon scope

**CONDITIONAL PASS** for cardiac physiology review of the Missing Piece evidence
map and perturbation policy.

**Accept** for demo and judge narrative when all of the following hold:

1. Evidence Priority Scores and completeness outputs stay labeled as **heuristic /
   proxy mapping** (`EDUCATIONAL_SCOPE`, audit `M8_MATH_AUDIT.md:300-326`).
2. Echo and BP mappings are described as **constraining declared indices**, not
   measuring contractility or SVR directly.
3. Perturbation results are described as **local deterministic sensitivity** at
   the audited 5% step (`M8_MATH_AUDIT.md:129-178`), not biological causal effects.
4. Default constraints come from `evidence_constraints()` so reviewed strengths
   match taxonomy (`evidence.py:89-92`).

**Not required for Tier-1** (would be post-hackathon physiology work): identifiable
splitting of afterload vs SVR from pressure alone, echo-derived multi-parameter
inversion, ECG beyond rate, or calibration of strength weights to real study data.

**Optional hardening** (small, non-blocking): single source for `EVIDENCE_MAP_VERSION`;
validate custom `EvidenceConstraint.strength` against taxonomy; route
`sensitivity.py` through `PerturbationPolicy`; use epsilon-based bound detection
in `perturbations.py:74-81`.

No runtime or live-clinical verification is claimed; this review is static
analysis of the listed sources and audit crosswalk.
