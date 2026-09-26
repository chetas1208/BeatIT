# BeatIT M3 Performance Notes

- Replay fixtures contain five bounded events and are reconstructed with pure
  cloning; this is appropriate for the demo but is not an unbounded event-log
  retention strategy.
- Playback is driven by one requestAnimationFrame loop in the provider. The
  heart's R3F loop remains independent, so historical scrubbing does not add a
  second animation loop to the canvas.
- Snapshot state is deeply detached and frozen. For production-scale histories,
  use checkpoint snapshots and windowed retention rather than cloning the full
  `CardiacTwinState` for every event.
- Timeline markers are rendered as a bounded list and the range input performs
  O(n) nearest-snapshot selection. Virtualization is unnecessary for the M3
  fixture but should be considered for thousands of snapshots.
- No benchmark claim is made here; browser profiling remains part of M4-scale
  data-volume validation.
