# BeatIT Model + Data Campaign Agent Plan

Status: active verification campaign, 2026-09-26 UTC

This campaign uses disjoint, evidence-first workstreams. Agents must inspect
the existing BeatIT seams before proposing implementation, keep all fixtures
synthetic, avoid printing secrets, and write only their assigned report unless
explicitly assigned a code/data artifact.

## Workstreams

1. Capability and model requirements
2. Hardware/runtime audit
3. Local model filesystem inventory
4. `/usr/data` model/data inventory
5. VISTA/MONAI compatibility
6. Language-model runtime
7. Model download/recovery decision
8. Local data inventory
9. Synthetic cohort generator
10. Synthetic ECG design
11. Cardiac enrichment/invariants
12. FHIR/schema validation
13. Cohort provenance
14. Cohort statistics/coverage
15. BeatIT ingestion
16. Persistence/restart
17. Multi-profile E2E
18. Cloudflare availability/tunnel
19. Public route verification
20. Browser/public E2E
21. PTB-XL reference boundary
22. NHANES reference boundary
23. Profile isolation
24. Probabilistic cohort QA
25. Shadow Trial cohort QA
26. Missing Piece cohort QA
27. Performance/load
28. Security/privacy
29. Model-runtime adversarial checks
30. Data-integrity adversarial checks
31. Tunnel security
32. Reproducibility
33. Documentation/source audit
34. Judge-style demo review

The commander counts only completed, technically substantive, reviewed scopes;
duplicate or document-only assertions without executable evidence do not count.
