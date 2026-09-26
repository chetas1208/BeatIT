# Performance Results (Certification Wave E4)

| Layer | Measurement (Wave 5–6) |
|-------|------------------------|
| Laya real (CPU) | ~105–325 ms/decision (fixture eval) |
| Fast Nemotron | 4–56 s (unsuitable for interactive fast path) |
| Deep Nemotron | ~7 successful billed calls; acceptable quality, use generous token budget |
| Tool dispatch | Sub-second for registry tools on local SQLite ensemble |
| Full suite | ~14 s for 1314 Python tests |

## Bottleneck

Interactive chat latency dominated by **deep/fast NVIDIA** when model path opens; production keeps clarification gate closed → mostly deterministic/clarification responses today.

## Frontend

Artifact chips O(1); panel uses single fetch per message (no streaming yet).
