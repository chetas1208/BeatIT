# BeatIT M3 QA

## Automated gates

Verified in the M3 workspace:

```bash
cd web
./node_modules/.bin/tsc --noEmit --pretty false
./node_modules/.bin/eslint components/heart components/charts components/layout components/twin lib/twin --max-warnings=0
./node_modules/.bin/next build
```

The focused TypeScript and lint gates passed. The production Next build
compiled, type-checked, prerendered the app routes, and completed optimization.

The M3 tests are standard-library `node:test` TypeScript files under the event,
reducer, and snapshot modules. The repository has no configured frontend test
runner, so they are included in the TypeScript build gate and should be wired to
the project's future frontend test command before CI promotion.

## Required behavioral checks

- Events reject invalid timestamps, duplicate conflicting IDs, unsafe payloads,
  and non-JSON values; identical duplicate IDs are idempotent.
- Out-of-order events reconstruct in deterministic chronological order.
- Reducer and snapshots do not mutate input state or event payloads.
- Timeline playback clamps to its range and supports pause, play, scrubbing,
  jump-to-live, and 0.5/1/2/5/10x rates.
- Timeline playback uses requestAnimationFrame deltas only; it does not modify
  `CardiacClock` heart rate or phase.
- Replay values carry synthetic provenance and the UI uses `REPLAY` outside the
  latest available cursor.

## Manual browser QA

Run `pnpm dev` from `web`, load a completed case, and verify:

1. The heart renders and continues beating while the history cursor is moved.
2. The timeline appears beneath the heart with markers, keyboard-accessible
   scrubber, play/pause, rates, and jump-to-live.
3. Scrubbing changes the displayed state, EF/heart-rate readouts, inspector
   report context, and simulation chart visualization.
4. The cursor can play through history while beat cadence continues.
5. Browser console has no errors during load, scrub, play, or jump-live.

Manual browser QA was not run in this headless implementation turn and remains
an explicit handoff item.
