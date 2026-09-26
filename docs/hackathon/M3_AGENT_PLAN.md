# BeatIT Milestone 3 Agent Plan

M3 turns the M2 cardiac snapshot into a deterministic, longitudinal twin. The
lead owns cross-cutting integration and the existing M1/M2 surfaces. Agents may
edit only the paths assigned below; they must preserve the M2 semantic registry,
the `CardiacClock`, and the distinction between history time and beat time.

## Shared contracts

The initial temporal contracts live in `web/lib/twin/time/contracts.ts`. Agents
must import those types rather than creating competing event or snapshot
shapes. State reconstruction remains pure and deterministic; no LLM or random
timer may calculate physiology.

## Ownership and expected outputs

| # | Workstream | Owned paths | Expected output |
|---|---|---|---|
| 1 | Temporal domain architect | `web/lib/twin/time/`, `docs/hackathon/M3_TEMPORAL_MODEL.md` | Timestamp, ordering, clock, and playback-domain contracts |
| 2 | Event store | `web/lib/twin/events/` | Append-only immutable event store with duplicate and out-of-order policy |
| 3 | State reconstruction | `web/lib/twin/reducer/` | Pure deterministic reducer and change log |
| 4 | Snapshot engine | `web/lib/twin/snapshots/` | Immutable snapshot construction and timeline reconstruction |
| 5 | Timeline/playback | `web/lib/twin/playback/` | Cursor, play/pause, rates, scrubbing, and jump-live controller |
| 6 | Timeline UI | `web/components/twin/timeline/` | Accessible timeline, markers, replay/live state, keyboard controls |
| 7 | Heart temporal adapter | `web/lib/twin/integration/` | Snapshot-to-M2 state/selection projection; no direct `HeartScene` edits |
| 8 | Temporal PV loop | `web/lib/twin/pv/` | Snapshot-aware PV adapter that keeps selected history separate from beat animation |
| 9 | ECG/signal timeline | `web/lib/twin/ecg/` | Measured/extracted/simulated/missing signal context with explicit provenance |
| 10 | Wearable source | `web/lib/twin/sources/wearable/` | Validated normalized wearable samples and source provenance |
| 11 | Replay fixture | `web/lib/twin/replay/`, `fixtures/longitudinal/` | Clearly synthetic deterministic replay stream and fixture states |
| 12 | Temporal provenance | `web/lib/twin/provenance/`, `web/components/twin/provenance/` | Evidence lineage model and compact provenance UI |
| 13 | Longitudinal history | `web/components/twin/history/` | History trend/readout component for selected snapshots |
| 14 | M3 QA/determinism | `web/lib/twin/**/__tests__/`, `docs/hackathon/M3_QA.md` | Focused tests for ordering, replay, immutability, clocks, and regression risks |
| 15 | Performance review | `docs/hackathon/M3_PERFORMANCE.md` | Render/retention guidance and measured risks |

The lead integrates the owned modules into `HeartScene`, `SimulationCharts`,
and `AppShell`, updates M3 decision/completion docs, runs all gates, and fixes
integration issues. Two independent adversarial reviewers will inspect the
integrated result after implementation and before completion.

## Integration rules

- `CardiacClock` remains the per-beat animation clock in milliseconds.
- `TimelineClock`/`PlaybackClock` advances historical timestamps only.
- Events are append-only. Corrections are new events, never edits in place.
- A replay/demo stream is labelled `REPLAY` or `DEMO STREAM`; `LIVE` means the
  latest available state, not a connected medical device.
- Interpolation is conservative: visual HR may interpolate; echo EF and AHA
  findings remain held/discrete unless explicitly simulated.
- Every agent reports changed files, tests, and any unresolved integration risk.
