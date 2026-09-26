# M5.5 Completion Record — Probabilistic Twin Closure

Last updated: 2026-09-26

## Status

**INCOMPLETE — M6 has not started.** The canonical backend path, durable local
storage, lineage policy, response contract, frontend adapter, uncertainty
surfaces, and validation repairs are implemented. Browser/accessibility QA and
some scientific closure gates remain open.

## Implemented

- Python validates a versioned `EnsembleResponse`, including sample counts,
  state projections, provenance, origin quality, and the canonical safety
  disclaimer.
- The active frontend plausible-twin flow calls `POST /api/v1/twin/ensemble`
  and maps the response. It no longer calls the local frontend runner.
- SQLite persistence stores the immutable JSON response by ensemble ID and
  survives a new store instance/process.
- Synthetic replay starts with `synthetic` quality and cannot be labeled
  `observed` when replay provenance is supplied.
- A golden fixed-afterload vector and backend response/persistence tests are
  present.
- PV-linked scalar uncertainty and a component uncertainty inspector are
  visible. Pointwise PV loop uncertainty is explicitly reported unavailable;
  no curve is fabricated from scalar percentiles.
- Python 3.13 test wrappers use `asyncio.run`; the full suite passes in the
  project environment.
- An alias-aware dependency-light frontend runtime harness tests both the
  distribution contract and backend response mapping.
- Current local performance evidence is recorded in
  [`M5_5_PERFORMANCE.md`](M5_5_PERFORMANCE.md); the API offloads CPU/SQLite work
  from the event loop.
- Full frontend lint has zero errors and two existing image-optimization
  warnings.

## Evidence

- `PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev pytest -q`: **796 passed, 1 skipped**.
- Focused ensemble/API/store/golden tests: **83 passed** in the latest run.
- `npx tsc --noEmit`: passed.
- `npm run test:runtime`: **2 passed**.
- `npm run lint`: **0 errors, 2 warnings**.
- Production build passed before the final documentation/QA edits; rerun after final edits before release.

## Open gates

- Browser interaction, responsive layout, keyboard, screen-reader, and visual
  QA are **BLOCKED — NOT RUN**: Playwright CLI is present, but no browser
  executable or Node browser-test harness is available.
- The golden vector currently proves the canonical backend evaluator, not
  cross-language numerical equivalence; equivalence is intentionally retired
  from the active frontend path.
- The backend ensemble projection remains separately versioned from the M4
  scenario evaluator (`m5.5-ensemble-projection-v1`); it is not claimed to be
  a clinical or M4-equivalent model.
- Persistence is local SQLite; a hosted multi-worker provider is not part of
  M5.5.
- Component uncertainty is scalar metric mapping, not anatomical geometry.
- The legacy frontend runner remains executable for historical tests, but is not
  imported by the active plausible-twin flow; repository-wide numerical
  retirement is therefore not claimed.

No M6/M7/M8 work is included in this record.
