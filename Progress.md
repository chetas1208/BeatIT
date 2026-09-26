# BeatIT Progress

Last updated: 2026-09-26

## Current status

M4 is implemented as a substantial foundation but remains **INCOMPLETE**. M5 is now under implementation and also remains **INCOMPLETE**. The current completion records are maintained in [`docs/hackathon/M4_COMPLETION.md`](docs/hackathon/M4_COMPLETION.md), [`docs/hackathon/M4_CLOSURE.md`](docs/hackathon/M4_CLOSURE.md), and [`docs/hackathon/M5_COMPLETION.md`](docs/hackathon/M5_COMPLETION.md).

M5.5 Probabilistic Twin Closure is **INCOMPLETE**; its detailed gate record is [`docs/hackathon/M5_5_COMPLETION.md`](docs/hackathon/M5_5_COMPLETION.md). M6/M7/M8 have not started.

## Completed

- BeatIT branding was applied while retaining DualBeat as the engine/research lineage.
- Local hardware, storage, runtime, and model inventory were audited without downloading model artifacts.
- A lazy model registry, safe model-status routes, optional VISTA-3D adapter, reconstruction mapping, and model tests were added.
- The M4 causal scenario engine supports immutable origins, bounded parameter validation, deterministic propagation, provenance, warnings, history, undo/redo, reports, and visualization projections.
- The scenario UI includes parameter controls, experiment/reset flows, causal graph rendering, scenario inspection, status announcements, and observed-baseline comparison.
- Frontend and backend documentation was added for model decisions, causal relationships, parameter ranges, QA, and the agent plan.
- The actual agent ledger records 24 dispatches and 16 meaningful completed contributions. The requested minimum of 20 meaningful contributions is not claimed.
- M5 now has typed parameter distributions, seeded sampling, rejection accounting, deterministic output distributions, provenance/version metadata, a Python API, and a plausible-twin UI mode.
- M5 records 22 completed meaningful, reviewed sub-agent contributions in [`docs/hackathon/M5_AGENT_PLAN.md`](docs/hackathon/M5_AGENT_PLAN.md); the agent-count gate is met, but M5 remains technically incomplete.
- M5.5 now has a separate coordination ledger in [`docs/hackathon/M5_5_AGENT_PLAN.md`](docs/hackathon/M5_5_AGENT_PLAN.md). Its backend contract, durable SQLite provider, explicit lineage policy, frontend response adapter, scalar uncertainty inspector, runtime harness, and credibility artifacts are implemented.

## Validation evidence

- Frontend TypeScript check: passed.
- Frontend production build: passed.
- Focused M4 ESLint checks: passed.
- Focused model and environment tests: 79 passed.
- Backend compile check and VISTA checkpoint CPU load: passed.
- M5 focused Python ensemble tests: 12 passed.
- M5 focused Python/API/cardio/model/schema regression: 141 passed, 0 failed, 0 skipped; 29 non-blocking Pydantic deprecation warnings.
- M5 local smoke benchmark: 50/100/250/500/1000 samples executed successfully; timings are explicitly non-baseline because independent single-repeat runs varied. Results and limitations are recorded in [`docs/hackathon/M5_PERFORMANCE.md`](docs/hackathon/M5_PERFORMANCE.md).
- M5 API smoke validation: POST creation and both GET retrieval routes returned 200 for a valid fixture; missing-resource behavior remains documented for route tests.
- Historical M5 baseline before M5.5 repairs: full backend had 718 passed, 10 Python 3.13 event-loop failures, and 1 skipped; full lint had 6 inherited errors. This is retained as historical evidence only.
- M5.5 repairs removed those event-loop/lint errors; current M5.5 evidence is below.
- Browser interaction, visual review, and assistive-technology validation have not yet been run.

### M5.5 validation evidence

- Project Python 3.13 suite via `PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev pytest -q`: **796 passed, 1 skipped**; SciPy is declared because the existing CareGuard imaging metrics require it.
- Focused ensemble/API/store/golden tests: **83 passed** in the latest run.
- Frontend `npx tsc --noEmit`: passed; `npm run test:runtime`: **2 passed**; `npm run lint`: **0 errors, 2 warnings** (existing dynamic-image warnings).
- No browser executable or Playwright installation is available, so browser/accessibility QA remains explicitly blocked rather than claimed.

## Open issues and risks

- The M5 minimum 20 meaningful-agent gate is met at 22; the separate M5.5 ledger records 20 completed, reviewed, non-duplicative contributions. Neither count waives the technical release gates below.
- Synthetic replay now begins with `synthetic` quality, suppresses live treatment, and is rejected when replay provenance is labeled observed; arbitrary caller-supplied lineage remains a trusted-network limitation.
- The scenario fork control exists but is not yet integrated into the primary timeline surface.
- Narrow-screen graph/table scrolling and final browser accessibility behavior need manual validation.
- M5.5 adds an alias-aware runtime harness; its Node experimental warnings are non-blocking.
- M5.5 ensemble retrieval is file-backed SQLite and restart-safe, but not an authenticated hosted multi-worker provider.
- Frontend/Python numerical parity is intentionally retired from the active path; backend golden vectors and a response-mapping test cover the canonical seam instead.
- Full-suite Python now passes; frontend lint has zero errors and two existing dynamic-image warnings.
- The backend projection and M4 scenario evaluator are explicitly versioned separately; cross-language numerical equivalence is not claimed. The active UI consumes backend output only.
- The current scalar EF/SV uncertainty surface does not provide pointwise PV uncertainty or anatomical component distributions.

## Next actions

1. Run browser, responsive, keyboard, and screen-reader QA when a browser executable and harness are available.
2. Decide whether to add authentication/restricted CORS and a hosted persistence provider before any real patient-data deployment.
3. Keep the legacy frontend runner quarantined or remove it in a separately reviewed cleanup; it is not active product behavior.
4. Re-run the production build and update `docs/hackathon/M5_5_COMPLETION.md` with final evidence.
5. Keep M5.5 incomplete and do not start M6/M7/M8 until the remaining gates are deliberately accepted.

## Real demo case campaign (2026-09-26)

- Strategy shift for **real** demos: MIMIC-IV + MIMIC-IV-ECG + MIMIC-IV-ECHO on one
  `subject_id`; PTB-XL / EchoNet as separate cases only.
- Wave 1 docs: `docs/data/REAL_DATA_*`, ledger `REAL_DEMO_CAMPAIGN_LEDGER.md`.
- **All waves executed:** `./scripts/run_real_demo_campaign.sh` — PTB-XL + MIMIC-IV Demo
  open data; **5 real cases** + hero `REAL-DEMO-PTB-000008`; artifacts under
  `data/real/` (gitignored). Multimodal MIMIC hero **blocked** (no credentialed access).
  See `docs/data/REAL_DEMO_CAMPAIGN_FINAL.md`.
