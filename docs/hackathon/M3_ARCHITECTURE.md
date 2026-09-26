# BeatIT M3 Architecture

M3 adds a longitudinal layer around the M2 cardiac viewport. The canonical
flow is:

```text
source adapters -> immutable TwinEventStore -> deterministic reducer
                                    -> immutable TwinSnapshots -> PlaybackClock
                                                              -> selected M2 state
```

`CardiacClock` continues to drive the visible heartbeat in milliseconds. A
separate timeline/playback clock moves through historical ISO-8601 timestamps.
Selecting a historical snapshot changes the state, findings, evidence, PV/ECG
context, and reports; it never changes the cardiac animation clock's heart rate
or phase contract.

## State boundaries

- `CardiacTwinState` remains the clinical snapshot shape from M1/M2.
- `TwinEvent` is append-only input. Corrections are new events with provenance.
- `TwinSnapshot` is immutable, serializable, and contains explicit evidence IDs,
  changes, quality, and provenance.
- Replay data is synthetic and explicitly labelled `REPLAY`/`DEMO STREAM`.
- `LIVE` means the latest available snapshot in the current source stream, not a
  medical-device connection.

The reducer accepts explicit paths and values and records every applied change.
It does not infer physiology, call an LLM, or fabricate missing data. PV and ECG
adapters preserve measured/extracted/simulated/missing distinctions.

## Integration seam

The lead-owned integration adapter projects a selected snapshot into the
existing `HeartScene`, inspector/report context, and charts. This keeps temporal
concerns out of the semantic registry and keeps the M1 beat clock independent of
history playback. The timeline is rendered beneath the heart viewport rather
than as a separate dashboard.
