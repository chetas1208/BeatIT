# M5 Performance

The runner accepts 50, 100, 250, 500, and 1000 samples. Benchmarks are not
claimed until executed on the target environment. The current physiology
calculation is small and deterministic; GPU execution is intentionally not
added for demonstration value without measured benefit.

## Local smoke benchmark (non-baseline)

Executed 2026-09-26 with Python 3.13.12, zero warmups, one repeat, and the
committed synthetic baseline fixture:

| Samples | Accepted | Mean wall time |
|---:|---:|---:|
| 50 | 50 | 0.63 ms |
| 100 | 100 | 0.92 ms |
| 250 | 250 | 2.20 ms |
| 500 | 500 | 7.97 ms |
| 1000 | 1000 | 9.48 ms |

This is one local smoke run, not a stable performance baseline. A later
independent rerun varied materially, so these values must not be used as a
capacity claim. They are not hardware-normalized or clinical performance
claims. They include ensemble result construction and summaries, but exclude
process startup and Pydantic request construction.
