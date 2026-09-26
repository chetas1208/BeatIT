# M5 Uncertainty Model

BeatIT distinguishes:

- measurement uncertainty: uncertainty attached to an observed value when a
  quantitative measurement error is actually available;
- parameter uncertainty: uncertainty in a model input proxy such as preload or
  contractility;
- population/model prior: an explicit bounded assumption used when patient
  evidence is absent;
- missing-evidence uncertainty: a record that evidence is absent, without
  fabricating a numeric estimate;
- simulation/output uncertainty: the distribution induced by accepted sampled
  inputs and deterministic physiology.

Existing `MeasuredValue.confidence` is a provenance/quality score, not a
statistical coverage probability. M5 does not reinterpret it.

