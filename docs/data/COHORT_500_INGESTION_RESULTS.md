# BeatIT Cohort 500 Ingestion Results

Command:

```bash
PYTHONPATH=. ./scripts/build-cohort-500.sh --reset
PYTHONPATH=. ./scripts/verify-cohort-500.sh
PYTHONPATH=. ./scripts/verify-cohort-advanced.sh
```

## Result

| Stage | Result |
|---|---:|
| Profiles attempted | 500 |
| Profiles successfully passed `python.hearttwin.orchestrator.run_full_pipeline` | 500 |
| Profiles failed | 0 |
| Profiles repaired silently | 0 |
| FHIR validation | 500 / 500 |
| SQLite persisted | 500 / 500 |
| Separate-process readback | 500 / 500 |
| Diverse ensemble checks | 120 / 120 |
| Diverse Shadow Trial checks | 120 / 120 |
| Diverse Missing Piece checks | 120 / 120 |
| Profile isolation IDs | 120 unique / 120 |

The ingestion path uses the actual deterministic BeatIT orchestrator. FHIR is
stored and structurally validated as synthetic evidence metadata; the current
cardiac orchestrator accepts normalized vitals rather than directly parsing a
FHIR Bundle. That boundary is explicit and is not represented as a nonexistent
FHIR-to-twin adapter.
