# M7 Clock Modes

## Phase locked

Both panes receive the same normalized cardiac phase. Mode label:
`SYNCED COMPARISON`. Baseline and counterfactual HR labels remain independent
and truthful. PV cursors use the same normalized phase.

## Physiologic rate

Each pane advances using its own modeled HR. Mode label: `PHYSIOLOGIC RATE`.
Unequal rates naturally drift in phase. Re-sync aligns the phase without
changing either HR.

The comparison clock is pure and immutable. A single requestAnimationFrame
owner advances comparison state; each heart consumes the supplied phase rather
than starting a second comparison timer.
