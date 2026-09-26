# BeatIT M3 Interpolation Policy

Interpolation is a display policy, never a replacement for evidence.

- Heart-rate display may interpolate between adjacent observed points when both
  points are numeric and the selected cursor is between them. The result is
  labelled derived/interpolated.
- Echo ejection fraction and other measured imaging values hold the last
  observed value until a newer observation exists.
- AHA findings, component evidence, and clinical annotations are discrete and
  change only at their event/snapshot boundary.
- PV curves use the selected snapshot's stored visualization. They are not
  re-simulated during a scrub and do not drive the beat animation.
- ECG remains explicitly measured, extracted, simulated, or missing. Missing
  signals are not synthesized to fill gaps.
- Synthetic replay values are marked synthetic and never presented as measured
  patient data.
