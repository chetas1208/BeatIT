# M8 Twin Completeness

Implementation: `python/hearttwin/missing_piece/completeness.py`.

## Domains (qualitative)

- **Electrical** — rhythm/rate evidence (e.g. repeat ECG)
- **Structural** — echo-derived LV function proxies
- **Hemodynamic** — pressure/SVR series
- **Longitudinal** — temporal coverage (M3-aware metadata when present)
- **Medication** — documented when medication provenance exists

Each domain reports **Strong / Moderate / Limited** (or unavailable) using explicit rules over `available_evidence_types` and the reviewed evidence map — not an arbitrary single percentage.

## Sensitivity availability

Completeness payload includes `sensitivity_availability` with contributing vs unavailable sample counts when projection bases are missing.
