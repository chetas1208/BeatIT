# BeatIT M3 Data Sources

M3 supports three bounded source classes:

1. Existing case extraction/operation results, carried into an initial
   `CardiacTwinState` and optional visualization.
2. Normalized clinical, ECG, and wearable events with source IDs, timestamps,
   units, confidence, and evidence lineage.
3. A deterministic synthetic replay fixture for the hackathon demo. It is
   labelled `REPLAY`/`DEMO STREAM` and is not a live device feed.

All timestamps must include a timezone. Events are stably ordered by timestamp,
then event ID. Duplicate IDs are rejected; corrections are appended as new
events. Payload values are preserved with provenance rather than silently
converted into diagnoses.
