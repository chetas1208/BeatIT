# M8 Browser & Accessibility Review

Status: **environment-blocked — not signed off**  
Date: 2026-09-26

## Attempted

- Next.js production build: **pass** (recorded in `M8_COMPLETION.md`).
- Direct HTTP smoke for `/`: **pass** where run.

## Blocked

- Playwright/Chromium: missing `libasound.so.2` on the validation host.
- Firefox: not installed.

## Static review (PASS, pending live AT)

- `MissingPiecePanel`: `aria-labelledby`, `aria-busy`, status region, explicit loading/error copy.
- `SensitivityTable`: sr-only caption, scoped headers, heuristic labels in footer.
- `UncertaintyOverlay`: textual scalar annotations; no color-only semantics claimed in code.

## Gate

Manual browser, keyboard-only, and screen-reader validation remain **open** until a supported browser runtime is available. M8 Tier-1 math/API gates do not depend on this signoff.
