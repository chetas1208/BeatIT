# BeatIT M1 baseline

Environment at audit time: Node `v22.22.2`, Python `3.13.x`, pnpm `11.23.0`.

| Command | Result |
| --- | --- |
| `python -m pytest python/hearttwin/tests --tb=short -q` | 664 passed, 1 skipped, 10 pre-existing failures |
| `python -c 'from python.hearttwin.api import app'` | passed / FastAPI app imports; live port verification was unavailable because the audit ports were already occupied |
| `pnpm -C web lint` | blocked by pnpm ignored build scripts (`sharp`, `unrs-resolver`, etc.) during install |
| `pnpm -C web build` | same dependency-install blocker |
| direct TypeScript/ESLint after dependency install | changed heart files lint clean; full build/typecheck still reports two pre-existing CareGuard type errors and full lint reports existing CareGuard hook/type errors |
| secret scan for key/token/private-key patterns | no matches |

The Python failures are in evaluator/validator tests using `asyncio.get_event_loop()` under the current Python runtime; they fail before the assertions and are unrelated to M1 frontend changes. No `.github` directory or inherited Git metadata exists in the BeatIT working copy.
