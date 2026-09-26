# BeatIT M3 longitudinal replay

The TypeScript generator in `web/lib/twin/replay` is the executable fixture.
It produces a stable five-event, two-day synthetic stream from any explicit
baseline `CardiacTwinState`. Every event is marked `synthetic_replay` with
`REPLAY`/`DEMO STREAM` provenance; these values are not patient measurements.
