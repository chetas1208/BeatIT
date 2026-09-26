# Failure Results (Certification Wave D)

| Scenario | Evidence |
|----------|----------|
| Laya offline | `test_certification_failure_matrix.py` — `LAYA_ENABLED=false`, safe response |
| All NVIDIA keys down | Mocked `ModelClientError` → safe fallback, no crash |
| 1–2 keys down | `test_model_reliability.py` — retry + success |
| 3 keys down | `NoHealthyKeyError` / `ModelClientError` — caller degrades |
| Safety model down | Deterministic `safety_validator` remains (always on) |

## Not live-tested this session

Real NVIDIA 429/503 storm — Wave 6 saw isolated 503 on deep model; quarantine behavior unit-tested only.
