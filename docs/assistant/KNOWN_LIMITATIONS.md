# Known Limitations — Unified Assistant

1. **Browser E2E** not Playwright-automated.  
2. **Fast NVIDIA model** unsuitable for interactive routing as configured.  
3. **Laya** zero-shot loses to deterministic fallback on most decision types; real Laya choice-wire bug documented in Wave 5 (choice decisions may fallback even when server up).  
4. **Six** adversarial safety gaps remain xfail.  
5. **Artifact detail views** only fully implemented for physician brief.  
6. **Server-side chat history** not persisted.  
7. ~~CopilotKit~~ retired; pipeline via REST + assistant tools.  
8. **Shadow trial / missing piece / scenario** not yet assistant tools — REST only.  
9. **Numeric validator** "45% EF" ordering gap.  
10. **case_context.py** not wired into orchestrator.
