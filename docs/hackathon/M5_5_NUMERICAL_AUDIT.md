# M5.5 Numerical Architecture Audit

Date: 2026-09-26  
Scope: active Python and frontend plausible-twin ensemble paths.  Read-only
audit; no M6, M7, or M8 work.

## Verdict

The active ensemble path is backend-authoritative:

1. `web/lib/twin/scenario/useScenario.tsx:110-118` calls
   `generateBackendEnsemble`.
2. `web/lib/twin/ensemble/backend.ts:52-67` sends distributions to
   `POST /twin/ensemble` and maps the response; it does not sample or evaluate
   physiology locally.
3. `python/hearttwin/api.py:156-168` runs `run_ensemble` and persists its
   result, while `web/lib/twin/ensemble/adapter.ts:5-67` performs field mapping
   only.
4. `web/components/twin/ensemble/PlausibleTwinsPanel.tsx:30-38` consumes the
   backend-selected representative IDs rather than selecting new samples.

That active seam satisfies the intended single numerical authority.  However,
the repository still contains a complete, importable legacy frontend numerical
runner.  It duplicates sampling, evaluation, rejection, statistics, and
representative selection and does not numerically agree with the Python
ensemble.  It is marked historical in `web/lib/twin/ensemble/index.ts:4-5`
and is not imported by the active UI, but it remains a future drift hazard and
must stay quarantined or be removed before claiming numerical closure.

## Authority and formula review

### Python active authority

- Parameter support and deterministic bounds are declared once for the backend
  ensemble in `python/hearttwin/ensemble.py:22-28`.
- Distribution validation checks the parameter set, support, family-specific
  parameters, and declared bounds in `python/hearttwin/ensemble.py:41-74`.
- Sampling uses one seeded local `random.Random` instance in
  `python/hearttwin/ensemble.py:353-358`; family draws are implemented in
  `python/hearttwin/ensemble.py:286-299`.
- The backend projection formula is in `python/hearttwin/ensemble.py:302-312`.
  It derives EDV, ESV, stroke volume, cardiac output, EF, and MAP from the
  sampled proxies without adding output noise.
- Accepted/rejected samples and physiological invariants are handled in
  `python/hearttwin/ensemble.py:357-368`; only accepted outputs enter summary
  distributions at `python/hearttwin/ensemble.py:368-372`.
- Empirical quantiles use sorted samples and linear interpolation at
  `(n - 1) * probability` in `python/hearttwin/ensemble.py:336-343`.
  Summary statistics use population variance and retain sorted samples in
  `python/hearttwin/ensemble.py:346-350`.
- Representative selection is deterministic and EF-based: low/high are the
  accepted EF extrema and median is the accepted sample nearest the EF median,
  at `python/hearttwin/ensemble.py:373-395`.

### Frontend active path

- The active request builder derives only distribution inputs in
  `web/lib/twin/ensemble/backend.ts:13-37` and serializes them at
  `web/lib/twin/ensemble/backend.ts:39-49`.
- Frontend bounds match the backend values in
  `web/lib/twin/scenario/parameters.ts:31-74` and backend ensemble bounds in
  `python/hearttwin/ensemble.py:22-28`.
- The active frontend does not run a competing sampler, physiology formula, or
  statistics reducer.  It maps backend samples and summaries unchanged in
  `web/lib/twin/ensemble/adapter.ts:14-64`.
- The active scalar uncertainty surface intentionally does not fabricate a
  pointwise PV envelope: `web/lib/twin/ensemble/pvEnvelope.ts:11-23`.
- `web/lib/twin/ensemble/visualization.ts:10-25` is a presentation projection
  of a selected backend sample.  Its RR calculation and held baseline PV shape
  are display behavior, not an alternative ensemble evaluator.

## Findings

### F1 — Retained frontend runner duplicates and diverges from the canonical evaluator

Severity: medium architectural risk; no current active-UI discrepancy found.

`web/lib/twin/ensemble/runner.ts:115-171` still implements a full local
ensemble, including seeded sampling, propagation, rejection, summaries, and
provenance.  It calls the M4 frontend evaluator
`web/lib/twin/scenario/propagation.ts:133-161`, whereas the active backend calls
`python/hearttwin/ensemble.py:302-312`.

The formulas are not equivalent:

- Python ESV uses `base["edv"] * 0.25` for the afterload term at
  `python/hearttwin/ensemble.py:308`.
- Frontend M4 ESV uses `base.sv * 0.55` at
  `web/lib/twin/scenario/propagation.ts:148-155`.
- Frontend M4 explicitly clamps SV and CO with `Math.max(1, ...)` and
  `Math.max(0.1, ...)` at `web/lib/twin/scenario/propagation.ts:153-155`; the
  backend computes these directly at `python/hearttwin/ensemble.py:309-312`.
- Frontend state projection rounds values to four decimals at
  `web/lib/twin/scenario/propagation.ts:164-188`; the backend projection does
  not round at `python/hearttwin/ensemble.py:315-333`.

This is acceptable only because the active UI reaches `backend.ts`, not
`runner.ts`.  The direct imports from `runner.ts` in
`web/lib/twin/ensemble/__tests__/runner.test.ts:5` and
`web/lib/twin/ensemble/__tests__/provenance.test.ts:5` prove that the path is
still maintained and executable.  It should remain explicitly test-only or be
deleted in a scoped cleanup; it must not be reconnected to the UI.

### F2 — PRNGs are duplicated and cannot provide cross-language sample equivalence

The active backend uses Python's `random.Random` at
`python/hearttwin/ensemble.py:353-358`.  The retained frontend path uses a
different custom PRNG at `web/lib/twin/ensemble/distributions.ts:9-20`.
Therefore identical seed/configuration values do not imply identical sampled
inputs across languages.  The active frontend correctly sends the seed to the
backend at `web/lib/twin/ensemble/backend.ts:52-66`, so this is not an active
runtime defect.  It is a closure risk if the legacy runner is ever promoted.

### F3 — Statistics and quantiles are duplicated, currently equivalent

The Python quantile and summary implementations are at
`python/hearttwin/ensemble.py:336-350`.  The retained frontend equivalents are
at `web/lib/twin/ensemble/statistics.ts:3-31`.

The implementations currently agree on the important policy: sorted empirical
samples, linear interpolation, population variance, and q05/q25/q75/q95.
The frontend function is used by `runner.ts:153`, not by the active backend
adapter.  Keeping two copies creates unnecessary future drift even though no
current statistical mismatch was observed.

### F4 — Rejection contracts are similar but not identical outside the active path

The backend requires exactly one distribution for every deterministic
parameter at `python/hearttwin/ensemble.py:98-104`, rejects out-of-declared
support without clamping at `python/hearttwin/ensemble.py:357-365`, and records
one sample for every requested draw at `python/hearttwin/ensemble.py:366-385`.

The retained frontend runner validates only non-empty distributions and
duplicate IDs at `web/lib/twin/ensemble/runner.ts:115-124`; missing parameters
are converted into per-sample rejection reasons at
`web/lib/twin/ensemble/runner.ts:37-52`.  Its rejected samples retain the
original snapshot state and only the successfully sampled parameter subset at
`web/lib/twin/ensemble/runner.ts:134-150`, whereas backend rejected samples
retain all sampled parameters, empty outputs, and the original state at
`python/hearttwin/ensemble.py:357-367`.

The shared rejection policy is therefore not a cross-language contract.  The
active path is safe because request validation and rejection happen in Python;
the frontend receives the already validated response.

### F5 — Representative selection is canonical only in the active backend path

The backend always returns EF-based representative IDs at
`python/hearttwin/ensemble.py:373-395`.  The active panel resolves those IDs
without recomputation at `web/components/twin/ensemble/PlausibleTwinsPanel.tsx:30-38`.

The retained runner has a separate `chooseRepresentatives` implementation at
`web/lib/twin/ensemble/runner.ts:193-200`.  It accepts an arbitrary metric and
recomputes the nearest-to-median sample from frontend summaries.  That can
disagree with the backend contract for non-EF metrics, and the backend response
does not return alternate metric representative IDs.  No active UI call to
this function was found; production import search shows only the two historical
test imports.

### F6 — Bound declarations match, but baseline handling has a wider internal clamp

The backend and frontend public ensemble/scenario bounds match exactly for all
five parameters: HR `[30, 200]`, preload `[0, 1.5]`, afterload `[0, 2]`,
contractility `[0, 1.5]`, and SVR `[0, 2]` (`python/hearttwin/ensemble.py:22-28`;
`web/lib/twin/scenario/parameters.ts:31-74`).

The backend baseline normalizer clamps HR to `[30, 220]` at
`python/hearttwin/ensemble.py:269-273`, and the frontend M4 baseline does the
same at `web/lib/twin/scenario/propagation.ts:108-114`.  This does not allow an
out-of-range sampled HR—the distribution validator still caps samples at 200—
but it means a source state at 201–220 can influence baseline normalization
while the public ensemble parameter support stops at 200.  This is a documented
boundary inconsistency to resolve only in a scoped numerical-contract change.

## Verification evidence

Read-only commands run from the repository:

```text
PYTHONPATH=. uv run --project . --extra dev pytest -q \
  python/hearttwin/tests/test_ensemble.py \
  python/hearttwin/tests/test_ensemble_api.py \
  python/hearttwin/tests/test_probabilistic_golden.py \
  python/hearttwin/tests/test_ensemble_store.py
39 passed in 1.37s

cd web && npm run test:runtime
2 passed

cd web && npx tsc --noEmit
passed with no output
```

The focused backend suite covers repeatability, changed seeds, rejection
accounting, physiological invariants, provenance, response validation, API
round trips, golden evaluation, and process persistence.  The frontend runtime
harness verifies deterministic distribution sampling and response mapping
without recomputing physiology.

## Recommendations / M5.5 boundary

- Keep `web/lib/twin/ensemble/backend.ts` plus `adapter.ts` as the only active
  frontend ensemble seam.
- Keep `runner.ts` and its direct tests clearly quarantined, or remove them in a
  separately authorized cleanup.  Do not start M6/M7/M8 to address this audit.
- If cross-language numerical equivalence is ever required, define one
  versioned PRNG and one evaluator contract first; do not silently align the
  current divergent formulas.
- Treat the matching statistics as a single policy and avoid adding another
  frontend summary implementation.

No M6, M7, or M8 work was performed.
