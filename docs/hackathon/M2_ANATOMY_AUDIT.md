# BeatIT M2 anatomy registry audit

Date: 2026-09-25  
Scope: `web/lib/heart/registry.ts` only

## Result

The registry covers the M2 addressable anatomy surface without adding unsupported
clinical structures:

| Category | Coverage | Registry IDs / evidence |
| --- | ---: | --- |
| Chambers | 4 | `left-atrium`, `right-atrium`, `left-ventricle`, `right-ventricle` |
| Valves | 4 | `mitral-valve`, `tricuspid-valve`, `aortic-valve`, `pulmonary-valve` |
| Major vessels | 5 | aorta, pulmonary artery, pulmonary veins, superior vena cava, inferior vena cava |
| Coronary territories | 3 | `lad`, `lcx`, `rca`; canonical values `LAD`, `LCX`, `RCA` |
| AHA myocardial segments | 17 | `aha-01` through `aha-17`, with numeric `ahaSegment` values 1 through 17 |
| Electrical structures | 6 | SA node, AV node, bundle of His, left/right bundle branches, Purkinje network |
| Functional layers | 6 | electrical propagation, blood flow, contraction, pathology, difference, uncertainty |

The anatomy descriptions and component categories are descriptive visualization
metadata. They do not assert a patient-specific diagnosis, treatment, or
imaging-derived anatomy.

## AHA-17 and coronary mapping

The registry's segment territory metadata is now aligned with the repository's
authoritative deterministic finding layer in
`python/hearttwin/tools/cardiac_findings.py`:

| AHA segments | Registry territory | Existing finding-layer evidence |
| --- | --- | --- |
| 1, 2, 7, 8, 13, 14, 17 | LAD | anterior, anteroseptal, and apical mappings |
| 3, 4, 9, 10, 15 | RCA | inferoseptal and inferior mappings |
| 5, 6, 11, 12, 16 | LCx / `LCX` | posterolateral and lateral mappings |

The source layer uses the spelling `LCx`; the TypeScript registry keeps the
canonical enum spelling `LCX`. Finding resolution now normalizes case and
spelling, so backend values such as `LCx` resolve to the registry's LCX
components. Unknown territory values are ignored rather than guessed.

Segment 17 is recorded as LAD only because the existing project finding layer
explicitly assigns its apical finding to LAD. This is a project-level binding,
not a claim that every clinical coronary model assigns the apex identically.
No additional segment-to-artery relationships were inferred.

## Finding resolution checks

`getComponentsForFinding` supports all existing finding forms:

- explicit component finding IDs, including AHA segment bindings;
- `aha_segments` arrays, including global `1..17` findings;
- coronary territory values from the backend (`LAD`, `RCA`, `LCx`) and the
  registry's canonical values.

Resolution now uses explicit boolean conditions to avoid accidental matches from
operator precedence and treats absent or unknown fields as no match.

## Changes made

- Corrected the 17-entry territory array to match the existing backend wall
  mappings.
- Normalized backend `LCx` territory values to the registry's `LCX` enum.
- Kept all existing IDs, categories, descriptions, bindings, and capabilities
  intact.

## Verification

Focused checks completed:

```text
Registry source inspection: 4 chambers, 4 valves, 5 vessels, 3 coronaries,
17 AHA segments, 6 electrical structures, and 6 functional layers.
Territory sequence: LAD LAD RCA RCA LCX LCX LAD LAD RCA RCA LCX LCX LAD LAD RCA LCX LAD.
Backend wall mappings agree for every explicitly listed segment.
```

The repository has no frontend unit-test script. The registry file was validated
with the focused ESLint command:

```bash
cd web
node_modules/.bin/eslint lib/heart/registry.ts --max-warnings=0
```

Full frontend build/typecheck remains outside this bounded task and is subject to
the pre-existing CareGuard errors documented in `docs/hackathon/M1_BASELINE.md`.
