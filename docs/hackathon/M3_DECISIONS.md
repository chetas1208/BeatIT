# BeatIT M3 Decisions

1. Keep `CardiacClock` and history playback clocks separate. The former owns
   beat animation; the latter owns historical cursor time.
2. Use immutable append-only events and detached frozen snapshots. Corrections
   are new state-update events with a `correctionOf` reference.
3. Use deterministic chronological ordering with stable event tie-breakers and
   explicit timestamp timezone requirements.
4. Keep reducer math opaque and evidence-driven. No LLM or frontend reducer
   computes physiology.
5. Make replay synthetic and visible. `REPLAY`/`DEMO STREAM` is provenance, not
   a hidden substitute for a medical-device connection.
6. Apply conservative temporal display policy: HR can be visually interpolated;
   EF, AHA findings, ECG data, and clinical evidence stay held/discrete.
7. Project the selected snapshot through a provider so the heart, reports, and
   PV chart consume one historical state without expanding the global store.
