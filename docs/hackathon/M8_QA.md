# M8 QA Record

## Automated gates

- Full Python suite passed: 1207 passed, 1 skipped, 6 expected failures.
- M8 focused suite passed: 64 passed.
- M8 Python lint passed with Ruff.
- Frontend TypeScript, scoped ESLint, direct Node runtime tests, and Next
  production build passed.
- API import exposes both Missing Piece routes and SQLite store tests pass.

## Safety and language checks

- All public Missing Piece responses use the canonical safety disclaimer.
- UI labels uncertainty-impact heuristic and Evidence Priority Score explicitly.
- No code path asks an LLM to choose perturbations, calculate derivatives, or
  assign evidence weights.
- Invalid samples and unavailable perturbations retain reasons; no values are
  fabricated.

## Open environment evidence

Manual browser, WebGL frame-time, keyboard/AT, and screen-reader evidence was
not claimed. The available local Chromium harness is missing `libasound.so.2`
and Firefox is not installed. These are documented blockers, not pass results.
