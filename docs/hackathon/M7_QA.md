# M7 QA Record

## Automated gates

- M7 comparison unit/runtime tests cover clock modes, transition interruption,
  camera model, semantic selection, difference thresholds, component model,
  and provenance.
- Frontend TypeScript, lint, runtime tests, and production build are required
  before completion.
- Backend regression remains required because M7 consumes M6 API contracts.

## Browser gate

The previous local browser attempt was blocked by missing `libasound.so.2` for
Chromium and absent Firefox. Direct HTTP success is not browser evidence. M7
must not claim keyboard, WebGL, responsive, or screen-reader sign-off until a
browser-capable environment completes the split flow.

## Required manual flow

Run a valid Shadow Trial, choose `Compare this pair`, verify two canvases and
pair IDs, toggle phase-locked/physiologic-rate modes, pause and scrub, select a
semantic component, enable difference-only mode, inspect PV cursor labels, and
close comparison. Check console warnings, NaN transforms, duplicate keys, and
WebGL resource cleanup.
