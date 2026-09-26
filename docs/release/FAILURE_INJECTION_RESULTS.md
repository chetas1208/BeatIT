# M10.5 Failure Injection Results

| Failure | Result | Boundary |
|---|---|---|
| Generic model disabled/unconfigured | PASS | deterministic fallback remains available |
| VISTA disabled | PASS | procedural heart path remains available |
| Internet/provider absent | PASS locally | external-provider live outage not exercised |
| Invalid ensemble | PASS | validation error, no fabricated result |
| Invalid scenario | PASS | HTTP 422, observed baseline unchanged |
| Missing backend resource | PASS | explicit 404/503 with disclaimer |
| Persistence error | PASS | safe service error; no secret/internal detail |
| Database/Redis outage | OPEN | external dependency fault injection not run |
| Model timeout | OPEN | only mocked/unit fallback evidence exists |
| Browser/network degradation | PARTIAL | Playwright smoke; full chaos OPEN |
| Repeatable probe | PASS | `./scripts/verify_failure_injection.py` in `--deep` |

No failure test is promoted to a deployment claim beyond its evidence scope.
