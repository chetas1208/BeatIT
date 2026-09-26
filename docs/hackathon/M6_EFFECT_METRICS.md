# M6 Effect Metrics

Every effect is calculated as `scenario value - baseline value` for the same
paired plausible twin.

| Metric | Unit | Near-zero tolerance |
|---|---|---:|
| Ejection fraction | percentage points | 0.01 |
| Stroke volume | mL | 0.01 |
| Cardiac output | L/min | 0.001 |
| Heart rate | bpm | 0.01 |
| Mean arterial pressure | mmHg | 0.01 |
| EDV / ESV | mL | 0.01 |

Statistics are descriptive summaries across valid paired simulations:
mean, median, q05, q25, q75, q95, and positive/near-zero/negative counts.
The q05–q95 range is not a confidence interval, credible interval, probability,
efficacy estimate, or patient-specific likelihood.

Positive, near-zero, and negative are neutral simulation categories. A positive
cardiac-output delta is not automatically medically better, and a negative
delta is not automatically medically harmful.

Pointwise PV loop uncertainty is not returned by M5.5. M6 refuses to fabricate
PV curves or envelopes from scalar percentiles.
