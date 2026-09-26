# M9 QA

## Automated evidence

The lead ran the direct frontend gates after the product-shell changes:

- TypeScript: passed with `web/node_modules/.bin/tsc --noEmit`.
- Scoped ESLint: passed for product shell and route files.
- Next production build: passed; routes include `/`, `/[mode]`, and the
  existing CareGuard pages.
- `pnpm -C web ...` remains environment-blocked by the repository's ignored
  build-script policy (`@scarf/scarf`, `es5-ext`, `sharp`, `unrs-resolver`);
  direct equivalent commands were used and are recorded as such.

## Mandatory manual journey

Not signed off in this environment. The required operator sequence is:

1. Open BeatIT and load the demo case.
2. In TWIN, inspect the heart, timeline, anatomy selection, and source badge.
3. Move to EXPERIMENT; run the causal branch and bounded Shadow Trial.
4. Move to COMPARE; inspect the Split Heart, phase mode, and difference view.
5. Move to EVIDENCE; inspect uncertainty, evidence, and source/provenance.
6. Move to REPORT; confirm ready/partial/unavailable sections and limitations.
7. Return to TWIN and confirm the case context remains intact.

The browser environment must provide Chromium/WebGL/audio dependencies or an
equivalent supported browser before this becomes a completion gate.
