# Patient / Context Isolation (Certification Wave D3)

## Target

**0 cross-profile leaks** on certification suite.

## Test

`test_certification_patient_isolation.py`:

- Two persisted ensembles, same `conversation_id`.
- Second turn uses ensemble B context.
- Response text must **not** contain ensemble A id; tool path executes for B.

**Result:** PASS (1314-test suite).

## UI

- Case switch resets conversation id + turns (`BeatITCopilotPanel`).
- CareGuard copilot remains separate store (justified second product).

## Remaining risk

Server-side conversation persistence not implemented — isolation is per-request context today.
